import asyncio
import typing as t
from asyncio import Task
from functools import cached_property
from typing import Any

from lib.__init__ import (
    OutputFormatter,
    printer_video_folder_path_info,
    resolve_conflict_path,
    use_proxy,
)
from lib.load_yaml_config import CFG
from lib.name_metadata import fmt_files, get_image_ext_basename
from lib.path import Path
from lib.save_json_data import save_json_data
from static.color import Color
from static.parameter import paramstore
from unit.__init__ import FilenameSanitizer
from unit.date.date import get_formatted_publish_date
from unit.foldermanger import IMGFolderManager
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Playback_info, Public_context
from unit.image.cache_image_info import CachePublicINFO
from unit.image.class_ImageDownloader import ImageDownloader
from unit.image.parse_playback_contexts import IMG_PlaybackContext
from unit.image.parse_public_contexts import IMG_PublicContext

logger = setup_logging("image", "mint")


ContextList = list[dict[str, Any]]


class IMGmediaDownloader:
    semaphore: asyncio.Semaphore = asyncio.Semaphore(28)

    def __init__(self, community_id: int, communityname: str) -> None:
        self.input_community_id: int = community_id
        self.input_communityname: str = communityname
        self._playback_info = None
        self._public_context = None

    @cached_property
    def Playback_info(self) -> Playback_info:
        if self._playback_info is None:
            self._playback_info = Playback_info()
        return self._playback_info

    @cached_property
    def Public_context(self) -> Public_context:
        if self._public_context is None:
            self._public_context = Public_context()
        return self._public_context

    async def process_single_media(self, public_ctx: IMG_PublicContext, playback_ctx: IMG_PlaybackContext) -> list[Path] | None:
        async with IMGmediaDownloader.semaphore:
            folder_mgr: IMGFolderManager = IMGFolderManager(public_ctx, self.input_communityname)
            parser: ImageUrlParser = ImageUrlParser(public_ctx, playback_ctx, self.input_communityname)
            folder, image_meta = await folder_mgr.create_image_folder()
            json_file_name, image_meta = self.json_file_name(public_ctx, image_meta)
            if folder is None:
                raise ValueError("Folder path is None")
            return await parser.parse_and_download(
                folder,
                Path(folder / FilenameSanitizer.sanitize_filename(json_file_name)),
                image_meta,
            )

    def json_file_name(self, public_ctx: IMG_PublicContext, image_meta: dict[str, str]) -> tuple[str, dict[str, str]]:
        CP: CachePublicINFO = CachePublicINFO(public_ctx, self.input_communityname)
        image_meta["date"] = get_formatted_publish_date(CP.published_at, fmt_files)
        image_meta["title"] = CP.title
        image_meta["artis"] = CP.community_name or self.input_communityname
        json_file_name: str = OutputFormatter(f"{CFG['output_template']['json_file_name']}").format(image_meta)
        self.image_meta: dict[str, str] = image_meta
        return f"{json_file_name}.json", image_meta

    async def get_content(self, media_id: str) -> tuple[IMG_PublicContext, IMG_PlaybackContext]:
        pub, play = await asyncio.gather(
            self.Public_context.get_public_context(media_id, use_proxy),
            self.Playback_info.get_playback_context(media_id, use_proxy),
            return_exceptions=True,
        )
        if isinstance(pub, BaseException) or isinstance(play, BaseException):
            raise RuntimeError(f"fetch failed for {media_id}. Public Error:{pub if isinstance(pub, BaseException) else 'None'}. Playback Error: {play if isinstance(play, BaseException) else 'None'}")
        return IMG_PublicContext(pub), IMG_PlaybackContext(play)

    async def fetch_and_process(self, media_id: str) -> list[Path] | None:
        public_ctx, playback_ctx = await self.get_content(media_id)
        return await self.process_single_media(public_ctx, playback_ctx)

    async def run_image_dl(self, media_ids: list[str]) -> None:
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}IMAGE")
        download_tasks = [asyncio.create_task(self.fetch_and_process(mid), name=mid) for mid in media_ids]
        await asyncio.gather(*download_tasks)


class ImageUrlParser:
    def __init__(
        self,
        public_ctx: IMG_PublicContext,
        _IMG_PlaybackContext: IMG_PlaybackContext,
        input_communityname: str,
    ) -> None:
        self.IMG_PlaybackContext: IMG_PlaybackContext = _IMG_PlaybackContext
        self.IMG_Publicinfo: IMG_PublicContext = public_ctx
        self._input_communityname: str = input_communityname

    @cached_property
    def CachePublicINFO(self) -> CachePublicINFO:
        return CachePublicINFO(self.IMG_Publicinfo, self._input_communityname)

    @cached_property
    def community_name(self) -> str:
        return self._input_communityname or self.CachePublicINFO.community_name

    @cached_property
    def custom_community_name(self) -> str:
        return self.CachePublicINFO.community_name or self._input_communityname

    @cached_property
    def fmt(self) -> str:
        return CFG["output_template"]["date_formact"]

    @cached_property
    def ImageDownloader(self) -> ImageDownloader:
        return ImageDownloader()

    def printer_image_info(self) -> None:
        logger.info(f"{Color.fg('magenta')}{self.CachePublicINFO.title} {Color.fg('cyan')}{self.community_name} {Color.fg('gray')}{self.CachePublicINFO.media_id}{Color.reset()}")

    async def image_task(
        self, folder_path: Path | None, image_meta: dict
    ) -> tuple[
        list[Task[None]],
        list[tuple[Path, bytes]],
    ]:
        """
        回傳 (write_tasks, success_pairs)
        - write_tasks: list of asyncio.Task that write bytes to disk (each returns None)
        - success_pairs: list of (Path, bytes) 已成功下載的資料
        """
        if folder_path is None:
            raise ValueError("folder_path is None")

        self.printer_image_info()

        semaphore = asyncio.Semaphore(2)

        async def limited_download(url: str | None, path: Path) -> tuple[Path, bytes | None]:
            if not url:
                return path, None
            async with semaphore:
                return await self._download(url, path)

        download_tasks: list[asyncio.Task[tuple[Path, bytes | None]]] = []
        for image in self.IMG_PlaybackContext.images:
            url: str | None = image.get("imageUrl")
            image_name: str = self.image_name(url, image_meta)
            image_file_path: Path = folder_path / image_name
            task = asyncio.create_task(limited_download(url, image_file_path))
            download_tasks.append(task)

        success_pairs: list[tuple[Path, bytes]] = []
        errors: list[BaseException] = []
        for done_future in asyncio.as_completed(download_tasks):
            try:
                path, content = await done_future
                if content is not None:
                    success_pairs.append((path, content))
            except Exception as exc:
                errors.append(exc)
                logger.exception("image download failed", exc_info=exc)

        write_tasks: list[asyncio.Task[None]] = [asyncio.create_task(self.ImageDownloader._write_to_file(resp, path)) for path, resp in success_pairs]
        return write_tasks, success_pairs

    async def json_task(self, json_path: Path) -> list[asyncio.Task[None]]:
        json_task = [asyncio.create_task(save_json_data(json_path, self.custom_community_name, self.community_name)._write_file(json_path, self.IMG_Publicinfo.to_json()))]
        return json_task

    async def parse_and_download(self, folder_path: Path | None, jsonfile_path: Path, image_meta: dict) -> list[Path] | None:
        if paramstore.get("nodl") is True:
            self.printer_image_info()
            return None

        success_pairs: list[tuple[Path, bytes]] = []
        write_tasks: list[Task[None]] = []
        json_task: list[Task[t.Any]] = []

        if paramstore.get("noimages") is not True and paramstore.get("nodl") is not True:
            write_tasks, success_pairs = await self.image_task(folder_path, image_meta)

        if paramstore.get("nojson") is not True and paramstore.get("nodl") is not True:
            json_path: Path = await resolve_conflict_path(jsonfile_path)

            printer_video_folder_path_info(
                json_path,
                json_path.name,
                f"{Color.fg('blue')}Json {Color.reset()}",
            )
            json_task = await self.json_task(json_path)

        all_tasks = write_tasks + json_task
        if all_tasks:
            await asyncio.gather(*all_tasks)
        return [p for p, _ in success_pairs]

    async def _download(
        self,
        url: str,
        file_path: Path,
    ) -> tuple[Path, bytes | None]:
        """下載回傳(path, response)不寫檔"""
        response = await self.ImageDownloader.download_image(url)
        return file_path, response

    def image_name(self, image_url: str | None, image_meta: dict):
        if image_url is None:
            raise ValueError("image_url is None")
        base_name, ext = get_image_ext_basename(image_url)
        image_meta["raw_name"] = base_name
        image_file_name: str = OutputFormatter(f"{CFG['output_template']['image_file_name']}").format(image_meta)
        image_file_name: str = FilenameSanitizer.sanitize_filename(image_file_name)
        return f"{image_file_name}{ext}"
