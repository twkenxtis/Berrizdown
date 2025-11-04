import asyncio
import shutil
from functools import cached_property
from typing import Any

import orjson

from berrizdown.lib.__init__ import (
    OutputFormatter,
    printer_video_folder_path_info,
    resolve_conflict_path,
    use_proxy,
)
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.name_metadata import fmt_dir, fmt_files, get_image_ext_basename, meta_name
from berrizdown.lib.path import Path
from berrizdown.lib.save_json_data import save_json_data
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.community.community import custom_dict
from berrizdown.unit.date.date import get_formatted_publish_date
from berrizdown.unit.foldermanger import CMTFolderManager
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import Arits, Translate
from berrizdown.unit.image.class_ImageDownloader import ImageDownloader

logger = setup_logging("cmt", "aluminum")


class CMT:
    def __init__(self, communityid: int, communityname: str) -> None:
        self.communityid: int = communityid
        self.communityname: str = communityname

    @cached_property
    def filenameSanitizer(self) -> "FilenameSanitizer":
        return FilenameSanitizer()

    async def normalize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        result = item.copy()
        title: str = result["body"][:64].replace("\n", " ").replace("\r", " ").strip()
        result["title"] = self.filenameSanitizer.sanitize_filename(title)
        result["mediaId"] = result.pop("postId")
        result["publishedAt"] = result.pop("createdAt")
        result["communityId"] = self.communityid
        result["communityname"] = self.communityname
        return result

    async def normalization(self, cmt_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tasks = [self.normalize_item(item) for item in cmt_data]
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
        return results


class MainProcessor:
    completed = 0

    """Parses data & image URLs and manages their download."""

    def __init__(
        self,
        cmt_media: dict,
        index: dict[str, Any],
        folder: Path,
        total: int,
        custom_community_name: str,
        community_name: str,
        input_community_name: str,
        cmt_meta: dict[str, str],
    ):
        self.index: dict[str, Any] = index
        self._cmt_media: dict = cmt_media
        self.folder_path: Path = Path(folder)
        self._custom_community_name: str = custom_community_name or community_name
        self._community_name: str = community_name or input_community_name
        self._input_community_name: str = input_community_name or community_name
        self.total: int = total
        self.cmt_meta: dict[str, str] = cmt_meta
        self.ImageDownloader: ImageDownloader = ImageDownloader()
        self.time_str: str = get_formatted_publish_date(self.index["publishedAt"], fmt_files)

    @cached_property
    def community_name(self) -> str:
        return self._community_name

    @cached_property
    def custom_community_name(self) -> str:
        return self._custom_community_name

    @cached_property
    def input_community_name(self) -> str:
        return self._input_community_name

    @cached_property
    def json_file_name(self) -> str:
        self.cmt_meta["date"] = self.time_str
        return OutputFormatter(f"{CFG['output_template']['json_file_name']}").format(self.cmt_meta)

    @cached_property
    def save_json_data(self):
        return save_json_data(self.folder_path, self.custom_community_name, self.community_name)

    def image_file_name(self, base_name: str) -> str:
        self.cmt_meta["date"] = self.time_str
        img_metadata = self.cmt_meta
        img_metadata["raw_name"] = base_name
        return OutputFormatter(f"{CFG['output_template']['image_file_name']}").format(img_metadata)

    async def parse_and_download(self) -> None:
        """Parse data image URLs and download them with concurrency control."""
        tasks = (
            asyncio.create_task(self.process_image()),
            asyncio.create_task(self.save_CMT_json()),
        )
        await asyncio.gather(*tasks)

    def make_cmt_link(self, data: dict[str, Any]) -> str:
        if self.index["replyInfo"]["isReply"] is True:
            return f"https://berriz.in/{self.community_name}/board/{data['board']['boardId']}/post/{data['mediaId']}?reply={self.index['replyInfo']['parentCommentSeq']}"
        else:
            return f"https://berriz.in/{self.community_name}/board/{data['board']['boardId']}/post/{data['mediaId']}?focus=comment"

    async def save_CMT_json(self) -> None:
        """Save CMT data to json file."""
        match paramstore.get("nojson"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}CMT JSON")
            case _:
                data = await JsonBuilder(self._cmt_media, self._cmt_media.get("element", {}).get("seq")).build_translated_json()
                json_data = orjson.dumps(
                    {
                        "CMT": self.index,
                        "info": data,
                        "link": self.make_cmt_link(self.index),
                    },
                    option=orjson.OPT_INDENT_2,
                )
                json_file_path = await resolve_conflict_path(Path.cwd() / Path(self.folder_path) / f"{self.json_file_name}.json")
                printer_video_folder_path_info(
                    json_file_path,
                    json_file_path.name,
                    f"{Color.fg('blue')}Json {Color.reset()}",
                )
                await self.save_json_data._write_file(json_file_path, json_data)

    async def process_image(self) -> None:
        if paramstore.get("nodl") is True or paramstore.get("noimages") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}CMT IMAGE")
        else:
            for x in self._cmt_media["media"]["photo"]:
                image_url: str = x.get("imageUrl", "NOIMAGE")
                if image_url.startswith("http"):
                    base_name, ext = get_image_ext_basename(image_url)
                    imagepath = Path(self.folder_path) / Path(f"{self.image_file_name(base_name)}{ext}")
                    image_bytes = await self.ImageDownloader.download_image(image_url)
                    await self.ImageDownloader._write_to_file(image_bytes, imagepath)


class RUN_CMT:
    def __init__(self, selected_media: list[dict[str, Any]], input_communityname: str) -> None:
        self.input_community_name = input_communityname
        self.selected_media: list[dict[str, Any]] = selected_media
        self.folder_name = set()

    @cached_property
    def foldermanger(self) -> "CMTFolderManager":
        return CMTFolderManager(self.input_community_name)

    @cached_property
    def fm(self) -> str:
        return CFG["donwload_dir_name"]["date_formact"]

    @cached_property
    def artis(self) -> Arits:
        return Arits()

    @cached_property
    def translate(self) -> Translate:
        return Translate()

    async def run_cmt_dl(self) -> None:
        """Top Async ENTER"""
        semaphore = asyncio.Semaphore(7)
        all_folders: list[Path] = []
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}CMT")

        async def process(index: dict[str, Any]) -> str:
            async with semaphore:
                try:
                    cmt_media: dict = await self.cmt_media(index)
                    folder, custom_community_name, community_name, cmt_meta = await self.folder(index)
                    self.printer_cmtinfo(index, custom_community_name, community_name)
                    if paramstore.get("nodl") is True:
                        return "NODL"
                    self.folder_name.add(index["title"])
                    all_folders.append(folder)
                    await MainProcessor(
                        cmt_media,
                        index,
                        folder,
                        len(self.selected_media),
                        custom_community_name,
                        community_name,
                        self.input_community_name,
                        cmt_meta,
                    ).parse_and_download()
                    return "OK"
                except asyncio.CancelledError:
                    await self.handle_cancel()
                    raise asyncio.CancelledError

        tasks = [asyncio.create_task(process(index)) for index in self.selected_media]
        await asyncio.gather(*tasks)

    async def cmt_media(self, index: dict[str, Any]) -> dict[str, Any]:
        data = await self.get_cmt_info(index["contentId"])
        logger.debug(data)
        return data

    async def get_cmt_info(self, comment_id: int) -> dict[str, Any]:
        try:
            response = await self.artis.comment(comment_id, use_proxy)
            if response is not None:
                return response.get("data", {}).get("content")
            raise ValueError("Response is None")
        except asyncio.CancelledError:
            await self.handle_cancel()
            raise asyncio.CancelledError

    async def folder(self, cmt_media: dict[str, Any]) -> tuple[Path, str, str, dict[str, str]]:
        custom_community_name = await custom_dict(self.input_community_name)
        time_str: str = get_formatted_publish_date(cmt_media["publishedAt"], fmt_dir)
        artis_name: str = cmt_media["userNickname"]
        if artis_name == custom_community_name:
            artis_name: str = artis_name.lower()
        cmt_meta: dict[str, str] = meta_name(time_str, cmt_media["title"], custom_community_name, artis_name)
        folder_name: str = OutputFormatter(f"{CFG['donwload_dir_name']['dir_name']}").format(cmt_meta)
        folder, community_name = await self.foldermanger.create_folder(
            folder_name,
            cmt_media["communityId"],
        )
        self.folder_path: Path = Path(folder)
        return self.folder_path, custom_community_name, community_name, cmt_meta

    async def handle_cancel(self) -> None:
        if self.folder_path.parent.iterdir():
            for all_folder in self.folder_path.parent.iterdir():
                path = self.folder_path.parent / all_folder
                E = not any(path.iterdir())
                if E and path.name.strip() in all_folder.name.strip():
                    logger.warning(f"async_dl_cancel: delete folder {Color.fg('light_gray')}{path}{Color.reset()}")
                    shutil.rmtree(path)

    async def get_data(self):
        for item in self.cmt_data:
            folder_name: str = self.folder_name(item)
            await self.foldermanger.create_folder(folder_name, item["communityId"])

    def printer_cmtinfo(self, index: dict[str, Any], custom_community_name: str, community_name: str) -> str:
        logger.info(
            f"{Color.fg('magenta')}{index['title']} "
            f"{Color.fg('cyan')}{custom_community_name or community_name} "
            f"{Color.fg('gray')}{index['mediaId']}{Color.reset()} "
            f"{Color.fg('yellow')}{index['userNickname']}{Color.reset()}"
        )


class JsonBuilder:
    def __init__(
        self,
        index: dict[str, Any],
        cmtid: str,
        use_proxy: bool = False,
    ) -> None:
        self.index: dict[str, Any] = index
        self.cmtid: str = cmtid
        self.use_proxy: bool = use_proxy

    @cached_property
    def translate(self) -> "Translate":
        return Translate()

    async def build_translated_json(self) -> dict[str, Any]:
        translations: dict[str, str] = await self.fetch_translations()
        eng: str = translations.get("en")
        jp: str = translations.get("jp")
        zhHant: str = translations.get("zh-Hant")
        zhHans: str = translations.get("zh-Hans")

        return self.get_json_formact(eng, jp, zhHant, zhHans)

    def get_json_formact(self, eng: str, jp: str, zhHant: str, zhHans: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index": self.index,
            "translations": {
                "en": eng,
                "jp": jp,
                "zh-Hant": zhHant,
                "zh-Hans": zhHans,
            },
        }
        return payload

    async def fetch_translations(self) -> dict[str, str]:
        tasks = [
            self.translate.translate_comment(self.cmtid, "en", self.use_proxy),
            self.translate.translate_comment(self.cmtid, "ja", self.use_proxy),
            self.translate.translate_comment(self.cmtid, "zh-Hant", self.use_proxy),
            self.translate.translate_comment(self.cmtid, "zh-Hans", self.use_proxy),
        ]

        try:
            results = await asyncio.gather(*tasks)
        except Exception as e:
            raise e
        return {
            "en": results[0],
            "jp": results[1],
            "zh-Hant": results[2],
            "zh-Hans": results[3],
        }
