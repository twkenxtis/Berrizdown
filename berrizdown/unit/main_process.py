import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any

import aiofiles
import yaml
from lib.lock_cookie import cookie_session
from lib.media_queue import MediaQueue
from lib.path import Path
from lock.donwnload_lock import UUIDSetStore
from static.color import Color
from static.parameter import paramstore
from static.route import Route

from unit.cmt.cmt import RUN_CMT
from unit.handle.handle_log import setup_logging
from unit.image.image import IMGmediaDownloader
from unit.media.drm import BerrizProcessor
from unit.notice.notice import RunNotice
from unit.post.post import Run_Post_dl

logger = setup_logging("main_process", "light_peach")


class DuplicateConfig:
    path: Path = Route().YAML_path

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: str) -> tuple[bool, bool, bool, bool]:
        return asyncio.run(cls._read_config(path))

    @staticmethod
    async def _read_config(path: str) -> tuple[bool, bool, bool, bool]:
        if not os.path.exists(path):
            logger.error(f"Config not found: {path}")
            sys.exit(1)

        async with aiofiles.open(path, encoding="utf-8") as f:
            raw = await f.read()

        try:
            cfg = yaml.safe_load(raw)
            overrides = cfg["duplicate"]["overrides"]
            image_dup = bool(overrides.get("image", False))
            video_dup = bool(overrides.get("video", False))
            post_dup = bool(overrides.get("post", False))
            notice_dup = bool(overrides.get("notice", False))
            cmt_dup = bool(overrides.get("cmt", False))
            return image_dup, video_dup, post_dup, notice_dup, cmt_dup
        except (KeyError, yaml.YAMLError) as e:
            logger.error(f"Error parsing {path}: {e}")
            sys.exit(1)

    @classmethod
    def get_image_dup(cls) -> bool:
        return cls.load(DuplicateConfig.path)[0]

    @classmethod
    def get_video_dup(cls) -> bool:
        return cls.load(DuplicateConfig.path)[1]

    @classmethod
    def get_post_dup(cls) -> bool:
        return cls.load(DuplicateConfig.path)[2]

    @classmethod
    def get_notice_dup(cls) -> bool:
        return cls.load(DuplicateConfig.path)[3]

    @classmethod
    def get_cmt_dup(cls) -> bool:
        return cls.load(DuplicateConfig.path)[4]


image_dup = DuplicateConfig.get_image_dup()
video_dup = DuplicateConfig.get_video_dup()
post_dup = DuplicateConfig.get_post_dup()
notice_dup = DuplicateConfig.get_notice_dup()
cmt_dup = DuplicateConfig.get_cmt_dup()


logger.info(f"Loaded duplicates → {Color.fg('coral')}image: {image_dup}, video: {video_dup}, {Color.fg('coral')}post: {post_dup}, notice: {notice_dup}, cmt: {cmt_dup}{Color.reset()}")


class MediaProcessor:
    """A class to process media items from a queue, handling VOD and photo items"""

    ProcessorFunc = Callable[[Any, Any], Awaitable[None]]

    def __init__(self, selected_media: dict[str, Any], community_id: int, communityname: str) -> None:
        """Initialize the MediaProcessor with a UUIDSetStore."""
        self.community_id: int = community_id
        self.communityname: str = communityname
        self.store: UUIDSetStore = UUIDSetStore()
        self.selected_media = selected_media
        # 實例變數的類型提示
        self.media_processors: dict[str, MediaProcessor.ProcessorFunc] = {
            "VOD": self._process_vod_items,
            "LIVE": self._process_vod_items,
            "PHOTO": self._process_photo_items,
            "POST": self._process_post_items,
            "NOTICE": self._process_notice_items,
            "CMT": self._process_cmt_items,
        }
        self.IMGmediaDownloader = IMGmediaDownloader(self.community_id, self.communityname)

    async def cookie_check(self, media_ids: list[str]) -> bool:
        if cookie_session == {} and paramstore.get("no_cookie") is True:
            logger.warning(f"{Color.fg('light_gray')}Cookies is required to download {Color.bg('crimson')}videos{Color.reset()}")
            logger.info(f"{Color.fg('gold')}Skip {media_ids} video download{Color.reset()}")
            return False
        elif cookie_session == {}:
            raise ValueError("Fail to get cookie correct")
        else:
            return True

    def print_process_items(self, media_ids: list[str], item_name: str) -> None:
        if len(media_ids) < 14:
            logger.info(
                f"{Color.fg('light_gray')}Processing {item_name} IDs:{Color.reset()} {Color.fg('periwinkle')}{media_ids}{Color.reset()} "
                f"{Color.fg('light_gray')}Count:{Color.reset()} {Color.fg('spring_green')}{len(media_ids)}{Color.reset()}"
            )
        else:
            logger.info(
                f"{Color.fg('light_gray')}Processing {item_name} IDs:{Color.reset()} {Color.fg('periwinkle')}{media_ids[-13:]} ...{Color.reset()} "
                f"{Color.fg('light_gray')}Count:{Color.reset()} {Color.fg('spring_green')}{len(media_ids)}{Color.reset()}"
            )

    def add_to_duplicate(self, ids: list[str]):
        for x in ids:
            x = str(x)
            self.store.add(x)

    async def _process_vod_items(self, media_idntype: list[tuple[str, str]]) -> None:
        """Process VOD items using BerrizProcessor"""
        match paramstore.get("key"):
            case True:
                self.print_process_items(media_idntype, media_idntype[0][1])
                tasks = [
                    asyncio.create_task(
                        BerrizProcessor(
                            media_id,
                            media_type,
                            self.selected_media,
                            self.communityname,
                        ).run()
                    )
                    for media_id, media_type in media_idntype
                ]
                await asyncio.gather(*tasks)
            case None:
                media_id_list = []
                self.print_process_items(media_idntype, "Media")
                for media_id, media_type in media_idntype:
                    media_id_list.append(media_id)
                    skip_media_id = await self._check_download_pkl(media_id)
                    if skip_media_id and video_dup is False:
                        await self._handle_choice(skip_media_id)
                        continue
                    if await self.cookie_check(media_idntype):
                        processor: BerrizProcessor = BerrizProcessor(
                            media_id,
                            media_type,
                            self.selected_media,
                            self.communityname,
                        )
                        await processor.run()
                if video_dup is False and paramstore.get("key") is None:
                    self.add_to_duplicate(media_id_list)

    async def _process_photo_items(self, media_idntype: list[str]) -> None:
        """Process a list of photo items concurrently."""
        self.print_process_items(media_idntype, "Photo")
        # Assuming run_image_dl can handle a list of media_idntype
        await self.IMGmediaDownloader.run_image_dl(media_idntype)
        if image_dup is False:
            self.add_to_duplicate(media_idntype)

    async def _process_post_items(self, post_ids: list[str]) -> None:
        """Process a list of photo items concurrently."""
        self.print_process_items(post_ids, "Post")
        # Assuming run_post_dl can handle a list of post_ids
        await Run_Post_dl(self.selected_media["post"], self.communityname).run_post_dl()
        if post_dup is False:
            self.add_to_duplicate(post_ids)

    async def _process_notice_items(self, notice_ids: list[str]) -> None:
        """Process a list of photo items concurrently."""
        self.print_process_items(notice_ids, "Notice")
        # Assuming run_notice_dl can handle a list of notice_ids
        await RunNotice(self.selected_media["notice"], self.communityname).run_notice_dl()
        if notice_dup is False:
            self.add_to_duplicate(notice_ids)

    async def _process_cmt_items(self, media_idntype: list[str]) -> None:
        """Process a list of photo items concurrently."""
        self.print_process_items(media_idntype, "CMT")
        await RUN_CMT(self.selected_media["cmt"], self.communityname).run_cmt_dl()
        if cmt_dup is False:
            self.add_to_duplicate(media_idntype)

    async def _check_download_pkl(self, media_id: str | int) -> str | None:
        """Check if media_id exists in the store."""
        media_id_str = str(media_id)
        # 如果任何一個重複檢查為 False 且存在於 store 中，則返回 media_id
        if any(dup is False for dup in [image_dup, video_dup, post_dup, notice_dup, cmt_dup]) and self.store.exists(media_id_str):
            return media_id_str
        return None

    async def _handle_choice(self, skip_media_id: str) -> None:
        """Handle skipping media from 'vods' and 'photos' 'lives' 'post' 'notice' that already exist."""
        for media_type in ("vods", "photos", "lives", "post", "notice", "cmt"):
            for item in self.selected_media.get(media_type, []):
                check_values = [item.get("mediaId"), item.get("postId"), item.get("contentId"), item.get("mediaId")[0] if item.get("mediaId") and isinstance(item.get("mediaId"), list) else None]
                check_values_str = [str(val) for val in check_values if val is not None]
                if skip_media_id in check_values_str:
                    title: str = item.get("title", "Unknown Title")
                    mediaType: str = item.get("mediaType") or item.get("contentType") or "Unknown Type"
                    logger.info(f"{Color.bg('crimson')}Already exists{Color.reset()}{Color.fg('light_gray')}, skip download {Color.reset()}{Color.fg('tomato')}{mediaType} - {Color.fg('amber')}{title}{Color.reset()}")
                    print(
                        f"{Color.bg('spring_aqua')}Disable this function by change setting ⤵ "
                        f"{Color.reset()}\n{Color.fg('yellow_ochre')}{Route().YAML_path} in {Color.fg('forest_green')}[duplicate:overrides]{Color.reset()}"
                    )

    async def process_media_queue(self, media_queue: MediaQueue) -> None:
        """Process all items in the media queue, batching PHOTO items for concurrent processing."""
        live_ids: list[str] = []  # Temporary list to collect MEDIA media IDs
        post_ids: list[str] = []  # Temporary list to collect POST media IDs
        photo_ids: list[str] = []  # Temporary list to collect PHOTO media IDs
        notice_ids: list[str] = []  # Temporary list to collect NOTICE media IDs
        cmt_ids: list[str] = []  # Temporary list to collect CMT media IDs
        tasks: list[asyncio.Task] = []  # List to collect async tasks
        while not media_queue.is_empty():
            item: tuple[str, str] | None = media_queue.dequeue()
            media_id: str
            media_type: str
            media_id, media_type = item
            skip_media_id: str | None = await self._check_download_pkl(media_id) if await self.check_duplicate(media_type) else None
            if skip_media_id:
                await self._handle_choice(skip_media_id)
                continue
            if media_type == "PHOTO":
                photo_ids.append(media_id)  # Collect PHOTO media IDs
            elif media_type in ("VOD", "LIVE"):
                live_ids.append((media_id, media_type))
            elif media_type == "POST":
                post_ids.append(media_id)  # Collect POST media IDs
            elif media_type == "NOTICE":
                notice_ids.append(media_id)  # Collect NOTICE media IDs
            elif media_type == "CMT":
                cmt_ids.append(media_id)  # Collect CMT media IDs

        # Process all collected VOD/LIVE media IDs concurrently
        if live_ids and await self.cookie_check(live_ids) is True:
            task: asyncio.Task = asyncio.create_task(self._process_vod_items(live_ids))
            tasks.append(task)
        # Process all collected PHOTO media IDs concurrently
        elif photo_ids:
            task: asyncio.Task = asyncio.create_task(self._process_photo_items(photo_ids))
            tasks.append(task)
        # Process all collected POST media IDs concurrently
        elif post_ids:
            task: asyncio.Task = asyncio.create_task(self._process_post_items(post_ids))
            tasks.append(task)
        # Process all collected NOTICE media IDs concurrently
        elif notice_ids:
            task: asyncio.Task = asyncio.create_task(self._process_notice_items(notice_ids))
            tasks.append(task)
        # Process all collected Content IDs concurrently
        elif cmt_ids:
            task: asyncio.Task = asyncio.create_task(self._process_cmt_items(cmt_ids))
            tasks.append(task)

        # Wait for all tasks to complete
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.warning(f"{Color.fg('yellow')}Media processing cancelled{Color.reset()}")

    async def check_duplicate(self, media_type: str) -> bool:
        if image_dup is False and media_type == "PHOTO":
            return True
        elif video_dup is False and media_type == "VOD" and paramstore.get("key") is None:
            return True
        elif post_dup is False and media_type == "POST":
            return True
        elif notice_dup is False and media_type == "NOTICE":
            return True
        elif cmt_dup is False and media_type == "CMT":
            return True
        return False
