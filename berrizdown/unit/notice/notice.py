import asyncio
import shutil
from functools import cached_property
from typing import Any

import orjson
from lib.__init__ import (
    File_date_time_formact,
    printer_video_folder_path_info,
    resolve_conflict_path,
)
from lib.path import Path
from lib.save_json_data import save_json_data
from static.color import Color
from static.parameter import paramstore
from unit.__init__ import FilenameSanitizer
from unit.foldermanger import NOTICEFolderManager
from unit.handle.handle_board_from import BoardNoticeINFO, NoticeINFOFetcher
from unit.handle.handle_log import setup_logging
from unit.notice.get_body_images import DownloadImage
from unit.notice.save_html import SaveHTML, open_template_post_html

logger = setup_logging("notice", "forest_green")


class MainProcessor:
    completed = 0

    """Parses data & image URLs and manages their download."""

    def __init__(
        self,
        notice_media: dict,
        folder: Path,
        total: int,
        custom_community_name: str,
        community_name: str,
        input_community_name: str,
    ):
        self._community_name: str = community_name
        self._custom_community_name: str = custom_community_name
        self._input_community_name: str = input_community_name
        self._notice_media = notice_media
        self.folder_path: Path = Path(folder)
        self.total = total

    @cached_property
    def fetcher(self) -> "NoticeINFOFetcher":
        return self._notice_media["fetcher"]

    @cached_property
    def community_name(self) -> str:
        return self._community_name or self._custom_community_name

    @cached_property
    def custom_community_name(self) -> str:
        return self._custom_community_name or self._community_name

    @cached_property
    def input_community_name(self) -> str:
        return self._input_community_name

    @cached_property
    def FDTF(self) -> "File_date_time_formact":
        return File_date_time_formact(self.fetcher, "NOTICE", self.community_name, self.input_community_name)

    @cached_property
    def json_file_name(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.FDTF.notice()[0])

    @cached_property
    def html_file_name(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.FDTF.notice()[1])

    @cached_property
    def body(self) -> str:
        return self.fetcher.get_body()

    @cached_property
    def title(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.fetcher.get_title())

    @cached_property
    def DownloadImage(self) -> "DownloadImage":
        return DownloadImage(
            self.body,
            self.folder_path,
            self.fetcher,
            self.community_name,
            self.custom_community_name,
            self.input_community_name,
        )

    @cached_property
    def save_json_data(self):
        return save_json_data(self.folder_path, self.custom_community_name, self.community_name)

    async def parse_and_download(self) -> None:
        """Parse data image URLs and download them with concurrency control."""
        tasks = (
            asyncio.create_task(self.process_html()),
            asyncio.create_task(self.process_image()),
            asyncio.create_task(self.save_notice_json()),
        )
        await asyncio.gather(*tasks)

    async def process_html(self) -> None:
        MainProcessor.completed += 1
        match paramstore.get("nohtml"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip save{Color.reset()} {Color.fg('light_gray')}NOTICE HTML")
            case _:
                ISO8601: str = self.fetcher.get_reservedAt()
                html_file: str = open_template_post_html()
                await SaveHTML(
                    self.title,
                    ISO8601,
                    self.body,
                    self.folder_path,
                    self.html_file_name,
                    html_file,
                ).update_template_file()

    async def save_notice_json(self) -> None:
        """Save notice data to json file."""
        match paramstore.get("nojson"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}NOTICE JSON")
            case _:
                data = dict(self._notice_media)
                data.pop("fetcher", None)

                json_data = orjson.dumps(data, option=orjson.OPT_INDENT_2)
                json_file_path = await resolve_conflict_path(Path.cwd() / Path(self.folder_path) / f"{self.json_file_name}.json")
                printer_video_folder_path_info(
                    json_file_path,
                    json_file_path.name,
                    f"{Color.fg('blue')}Json {Color.reset()}",
                )
                await self.save_json_data._write_file(json_file_path, json_data)

    async def process_image(self) -> None:
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}NOTICE IMAGE")
        else:
            await self.DownloadImage.start_download_images()


class RunNotice:
    def __init__(self, selected_media: list[dict], input_communityname: str):
        self.input_community_name = input_communityname
        self.selected_media: list[dict[str, Any]] = selected_media
        self.folder_name = set()

    @cached_property
    def folder_manager(self) -> NOTICEFolderManager:
        return NOTICEFolderManager(self.input_community_name)

    async def run_notice_dl(self) -> None:
        """Top Async ENTER"""
        semaphore = asyncio.Semaphore(7)
        all_folders: list[Path] = []
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}NOTICE")

        async def process(index: dict[str, Any]) -> str:
            async with semaphore:
                try:
                    notice_media: dict | None = await self.notice_media(index)
                    match notice_media:
                        case None:
                            return "NODATA"
                        case _:
                            folder, custom_community_name, community_name = await self.folder(notice_media)
                            self.printer_noticeinfo(notice_media, custom_community_name, community_name)
                            if paramstore.get("nodl") is True:
                                return "NODL"
                            self.folder_name.add(notice_media["safe_title"])
                            all_folders.append(folder)
                            await MainProcessor(
                                notice_media,
                                folder,
                                len(self.selected_media),
                                custom_community_name,
                                community_name,
                                self.input_community_name,
                            ).parse_and_download()
                            return "OK"
                except asyncio.CancelledError:
                    await self.handle_cancel()
                    raise asyncio.CancelledError

        tasks = [asyncio.create_task(process(index)) for index in self.selected_media]
        await asyncio.gather(*tasks)

    async def notice_media(self, index: dict[str, Any]) -> dict[str, Any]:
        data = await self.get_notice_info(index, index["mediaId"], index["communityId"])
        logger.debug(data)
        return data

    async def folder(self, notice_media: dict[str, Any]) -> tuple[Path, str, str]:
        folder, custom_community_name, community_name = await self.folder_manager.create_folder(
            notice_media["folderName"],
            notice_media["communityId"],
        )
        self.folder_path: Path = Path(folder)
        return self.folder_path, custom_community_name, community_name

    async def get_notice_info(self, media: dict[str, Any], communityNoticeId: int, communityId: int) -> dict[str, Any]:
        try:
            get_notice_info_task = BoardNoticeINFO(media).request_notice_info(communityNoticeId, communityId)
            return await get_notice_info_task
        except asyncio.CancelledError:
            await self.handle_cancel()
            raise asyncio.CancelledError

    async def handle_cancel(self) -> None:
        if self.folder_path.parent.iterdir():
            for all_folder in self.folder_path.parent.iterdir():
                path = self.folder_path.parent / all_folder
                E = not any(path.iterdir())
                if E and path.name.strip() in all_folder.name.strip():
                    logger.warning(f"async_dl_cancel: delete folder {Color.fg('light_gray')}{path}{Color.reset()}")
                    shutil.rmtree(path)

    def printer_noticeinfo(
        self,
        notice_media: dict[str, Any],
        custom_community_name: str,
        community_name: str,
    ) -> None:
        logger.info(f"{Color.fg('magenta')}{notice_media['safe_title']} {Color.fg('cyan')}{custom_community_name or community_name} {Color.fg('gray')}{notice_media['notice_list']['mediaId']}{Color.reset()}")
