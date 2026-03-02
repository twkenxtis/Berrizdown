import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import aiofiles
import yaml

from berrizdown.lib.lock_cookie import cookie_session
from berrizdown.lib.media_queue import MediaQueue
from berrizdown.lib.path import Path
from berrizdown.lock.donwnload_lock import UUIDSetStore
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.route import Route
from berrizdown.unit.cmt.cmt import RUN_CMT
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.image.image import IMGmediaDownloader
from berrizdown.unit.media.drm import BerrizProcessor
from berrizdown.unit.notice.notice import RunNotice
from berrizdown.unit.post.post import Run_Post_dl

logger = setup_logging("main_process", "light_peach")


class DuplicateConfig:
    path: Path = Route().YAML_path

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: str) -> tuple[bool, bool, bool, bool, bool]:
        return asyncio.run(cls._read_config(path))

    @staticmethod
    async def _read_config(path: str) -> tuple[bool, bool, bool, bool, bool]:
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


type ProcessorFunc = Callable[[list[Any]], Awaitable[None]]


@dataclass
class MediaProcessor:
    """Process media items from a queue, handling VOD, LIVE, PHOTO, POST, NOTICE, CMT"""

    selected_media: dict[str, Any]
    community_id: int
    community_name: str

    store: UUIDSetStore = field(default_factory=UUIDSetStore)
    _img_downloader: IMGmediaDownloader = field(init=False)
    _media_processors: dict[str, ProcessorFunc] = field(init=False)

    def __post_init__(self) -> None:
        self._img_downloader = IMGmediaDownloader(self.community_id, self.community_name)
        self._media_processors: dict[str, ProcessorFunc] = {
            "VOD": self._process_vod_items,
            "LIVE": self._process_vod_items,
            "PHOTO": self._process_photo_items,
            "POST": self._process_post_items,
            "NOTICE": self._process_notice_items,
            "CMT": self._process_cmt_items,
        }

    async def cookie_check(self, media_ids: list[str] | list[tuple[str, str]]) -> bool:
        if cookie_session == {} and paramstore.get("no_cookie") is True:
            logger.warning(
                f"{Color.fg('light_gray')}Cookies is required to download "
                f"{Color.bg('crimson')}videos{Color.reset()}"
            )
            logger.info(f"{Color.fg('gold')}Skip {media_ids} video download{Color.reset()}")
            return False
        if cookie_session == {}:
            raise ValueError("Failed to obtain valid cookie")
        return True

    def print_process_items(self, media_ids: list[Any], item_name: str) -> None:
        display: list[tuple[str, str]] = media_ids if len(media_ids) < 14 else media_ids[-13:]
        suffix: str = "" if len(media_ids) < 14 else " ..."
        logger.info(
            f"{Color.fg('light_gray')}Processing {item_name} IDs:{Color.reset()} "
            f"{Color.fg('periwinkle')}{display}{suffix}{Color.reset()} "
            f"{Color.fg('light_gray')}Count:{Color.reset()} "
            f"{Color.fg('spring_green')}{len(media_ids)}{Color.reset()}"
        )

    def add_to_duplicate(self, ids: list[Any]) -> None:
        for media_id in ids:
            self.store.add(str(media_id))

    def check_duplicate(self, media_type: str) -> bool:
        """Return True if duplicate-check is active for this media_type."""
        rules: dict[str, bool] = {
            "PHOTO": image_dup is False,
            "VOD": video_dup is False and paramstore.get("key") is None,
            "LIVE": video_dup is False and paramstore.get("key") is None,
            "POST": post_dup is False,
            "NOTICE": notice_dup is False,
            "CMT": cmt_dup is False,
        }
        return rules.get(media_type, False)

    async def _process_vod_items(self, media_idntype: list[tuple[str, str]]) -> None:
        """Process VOD/LIVE items using BerrizProcessor."""
        match paramstore.get("key"):
            case True:
                self.print_process_items(media_idntype, media_idntype[0][1])
                tasks = [
                    asyncio.create_task(
                        BerrizProcessor(
                            media_id, media_type, self.selected_media, self.community_name
                        ).run()
                    )
                    for media_id, media_type in media_idntype
                ]
                await asyncio.gather(*tasks)
            case None:
                self.print_process_items(media_idntype, "Media")
                media_id_list: list[str] = []
                for media_id, media_type in media_idntype:
                    media_id_list.append(media_id)
                    if await self._check_download_pkl(media_id) and video_dup is False:
                        await self._handle_choice(media_id)
                        continue
                    if await self.cookie_check(media_idntype):
                        await BerrizProcessor(
                            media_id, media_type, self.selected_media, self.community_name
                        ).run()
                if video_dup is False:
                    self.add_to_duplicate(media_id_list)

    async def _process_photo_items(self, media_ids: list[str]) -> None:
        self.print_process_items(media_ids, "Photo")
        await self._img_downloader.run_image_dl(media_ids)
        if image_dup is False:
            self.add_to_duplicate(media_ids)

    async def _process_post_items(self, post_ids: list[str]) -> None:
        self.print_process_items(post_ids, "Post")
        await Run_Post_dl(self.selected_media["post"], self.community_name).run_post_dl()
        if post_dup is False:
            self.add_to_duplicate(post_ids)

    async def _process_notice_items(self, notice_ids: list[str]) -> None:
        self.print_process_items(notice_ids, "Notice")
        await RunNotice(self.selected_media["notice"], self.community_name).run_notice_dl()
        if notice_dup is False:
            self.add_to_duplicate(notice_ids)

    async def _process_cmt_items(self, cmt_ids: list[str]) -> None:
        self.print_process_items(cmt_ids, "CMT")
        await RUN_CMT(self.selected_media["cmt"], self.community_name).run_cmt_dl()
        if cmt_dup is False:
            self.add_to_duplicate(cmt_ids)

    async def _check_download_pkl(self, media_id: str | int) -> str | None:
        """Return media_id string if it already exists in the store, else None."""
        media_id_str = str(media_id)
        active: bool = any(
            dup is False for dup in (image_dup, video_dup, post_dup, notice_dup, cmt_dup)
        )
        return media_id_str if active and self.store.exists(media_id_str) else None

    async def _handle_choice(self, skip_media_id: str) -> None:
        """Log and notify that a duplicate item is being skipped."""
        for media_type in ("vods", "photos", "lives", "post", "notice", "cmt"):
            for item in self.selected_media.get(media_type, []):
                raw_media_id = item.get("mediaId")
                first_media_id = (
                    raw_media_id[0]
                    if isinstance(raw_media_id, list) and raw_media_id
                    else None
                )
                candidates = [
                    item.get("mediaId"),
                    item.get("postId"),
                    item.get("contentId"),
                    first_media_id,
                ]
                if skip_media_id not in {str(v) for v in candidates if v is not None}:
                    continue
                title: str = item.get("title", "Unknown Title")
                media_type_label: str = (
                    item.get("mediaType") or item.get("contentType") or "Unknown Type"
                )
                logger.info(
                    f"{Color.bg('crimson')}Already exists{Color.reset()}"
                    f"{Color.fg('light_gray')}, skip download {Color.reset()}"
                    f"{Color.fg('tomato')}{media_type_label} - "
                    f"{Color.fg('amber')}{title}{Color.reset()}"
                )
                print(
                    f"{Color.bg('spring_aqua')}Disable this function by changing setting ⤵"
                    f"{Color.reset()}\n"
                    f"{Color.fg('yellow_ochre')}{Route().YAML_path} "
                    f"in {Color.fg('forest_green')}[duplicate:overrides]{Color.reset()}"
                )

    async def process_media_queue(self, media_queue: MediaQueue) -> None:
        """Drain the queue, bucket items by type, then dispatch all concurrently."""
        live_ids: list[tuple[str, str]] = []
        photo_ids: list[str] = []
        post_ids: list[str] = []
        notice_ids: list[str] = []
        cmt_ids: list[str] = []

        while not media_queue.is_empty():
            media_id, media_type = media_queue.dequeue()
            if self.check_duplicate(media_type) and await self._check_download_pkl(media_id):
                await self._handle_choice(str(media_id))
                continue
            match media_type:
                case "PHOTO":
                    photo_ids.append(media_id)
                case "VOD" | "LIVE":
                    live_ids.append((media_id, media_type))
                case "POST":
                    post_ids.append(media_id)
                case "NOTICE":
                    notice_ids.append(media_id)
                case "CMT":
                    cmt_ids.append(media_id)

        tasks: list[asyncio.Task] = []

        if live_ids and await self.cookie_check(live_ids):
            tasks.append(asyncio.create_task(self._process_vod_items(live_ids)))
        if photo_ids:
            tasks.append(asyncio.create_task(self._process_photo_items(photo_ids)))
        if post_ids:
            tasks.append(asyncio.create_task(self._process_post_items(post_ids)))
        if notice_ids:
            tasks.append(asyncio.create_task(self._process_notice_items(notice_ids)))
        if cmt_ids:
            tasks.append(asyncio.create_task(self._process_cmt_items(cmt_ids)))

        if tasks:
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.warning(f"{Color.fg('yellow')}Media processing cancelled{Color.reset()}")

    def check_duplicate(self, media_type: str) -> bool:
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
