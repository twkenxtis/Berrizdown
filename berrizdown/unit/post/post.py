import asyncio
import shutil
from collections.abc import Awaitable, Callable
from functools import cached_property
from typing import Any, TypeAlias

from lib.__init__ import File_date_time_formact, OutputFormatter
from lib.load_yaml_config import CFG
from lib.name_metadata import fmt_files, get_image_ext_basename, meta_name
from lib.path import Path
from static.color import Color
from static.parameter import paramstore
from unit.__init__ import FilenameSanitizer
from unit.date.date import get_formatted_publish_date
from unit.foldermanger import POSTFolderManager
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Arits, Translate
from unit.image.class_ImageDownloader import ImageDownloader
from unit.post.postjsondata import PostJsonData
from unit.post.save_html import SaveHTML, open_template_post_html

logger = setup_logging("post", "daffodil")
semaphore = asyncio.Semaphore(7)
URL: TypeAlias = str


class MainProcessor:
    created_folders = set()

    def __init__(
        self,
        post_media: dict,
        folder: Path,
        community_name: str,
        custom_community_name: str | None,
    ):
        self._FDTF = File_date_time_formact(post_media, "POST", community_name)
        self._imagedownloader: ImageDownloader | None = None
        self.post_media: Any = post_media
        self.avatar_link: URL = self.post_media["index"]["writer"]["imageUrl"]
        self.body: str = self.post_media["index"]["post"]["body"]
        self.communityId: int = self.post_media["communityId"]
        self.community_name: str | None = community_name or custom_community_name
        self.fetcher: Any = post_media["fetcher"]
        self.folder_path: Path = Path(folder)
        self.time: str = self.post_media["publishedAt"]
        self.title: str = self.post_media["title"]

    @cached_property
    def post_id(self) -> int:
        return self.fetcher.get_postid()

    @cached_property
    def file_names(self) -> tuple[str, str]:
        return self._FDTF.post()

    @cached_property
    def json_file_name(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.file_names[0])

    @cached_property
    def html_file_name(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.file_names[1])

    @cached_property
    def json_data_obj(self) -> Any:
        return PostJsonData(
            self.post_media["index"],
            self.post_id,
            self.json_file_name,
            self.community_name,
        )

    @cached_property
    def artis(self) -> str:
        A: str = self.post_media["writer_name"]
        if self.community_name == A:
            return A.lower()
        return A

    @cached_property
    def imagedownloader(self) -> ImageDownloader:
        if self._imagedownloader is None:
            self._imagedownloader = ImageDownloader()
        return self._imagedownloader

    @cached_property
    def board_name(self) -> str:
        return self.fetcher.get_board_name()

    def printer_post_info(self) -> None:
        logger.info(f"{Color.fg('magenta')}{self.title} {Color.fg('cyan')}{self.community_name} {Color.fg('gray')}{self.post_id}{Color.reset()}")

    async def save_json_file(self, folder_path: Path) -> Path | None:
        self.printer_post_info()
        if paramstore.get("nodl") is True:
            return Path("")
        return await self.json_data_obj.save_json_file_to_folder(folder_path)

    def parse_list_images(self, data: dict[str, Any]) -> list[str]:
        List_images: list[str] = []
        for img_url in data.get("imageInfo", []):
            List_images.append(img_url)
        return List_images

    async def request_image(self, image_url: str) -> bytes | None:
        response = await self.imagedownloader.download_image(image_url)
        return response

    async def write_image_to_file(self, response: bytes, img_file_path: Path) -> None:
        await self.imagedownloader._write_to_file(response, img_file_path)

    async def process_image(self, list_images: list[str]) -> tuple[list[str], list[Path]]:
        return await self.get_img_url_path(list_images)

    async def get_img_url_path(self, image_list: list[URL]) -> tuple[list[str], list[Path]]:
        if paramstore.get("nodl") is True:
            return [""], [Path("")]
        img_file_path_list: list[Path] = []
        for image_url in image_list[1]:
            try:
                base_name, ext = get_image_ext_basename(image_url)
                dt: str | None = get_formatted_publish_date(self.time, fmt_files)
                post_meta: dict = meta_name(
                    dt,
                    self.title,
                    self.community_name,
                    self.artis,
                )
                post_meta["raw_name"] = base_name
                _image_name: str = OutputFormatter(f"{CFG['output_template']['image_file_name']}").format(post_meta)
                output_image_name: str = f"{_image_name}{ext}"
                img_file_path = self.folder_path / output_image_name
                logger.debug(f"Downloading: {image_url} → \n{img_file_path}")
                img_file_path_list.append(img_file_path)
            except Exception as e:
                logger.warning(f"Failed to download image {image_url}: {e}")
        return image_list, img_file_path_list

    async def process_html(self, folder_path: str | Path) -> None:
        if paramstore.get("nodl") is True:
            return
        folder_path = Path(folder_path)
        if paramstore.get("nohtml") is True:
            logger.info(f"{Color.fg('light_gray')}Skip save{Color.reset()} {Color.fg('light_gray')}POST HTML")
            return
        html_file: str = open_template_post_html()
        html_generator = SaveHTML(
            self.title,
            self.time,
            self.make_body(self.fetcher.get_photos()[1]),
            self.artis,
            folder_path,
            self.avatar_link,
            self.html_file_name,
            self.board_name,
            html_file,
        )
        await html_generator.update_template_file()

    def make_body(self, image_list: list[str] | str) -> str:
        if image_list != "NOIMAGE":
            html_parts = [f"<p>{self.body}</p><br>"]
            html_parts += [f'<p><img src="{url}"></p><br>' for url in image_list]
            return "".join(html_parts)
        return f"<p>{self.body}</p>"


class Run_Post_dl:
    def __init__(self, selected_media: list[dict], community_name: str):
        self.selected_media = selected_media
        self.input_community_name: str = community_name

    @cached_property
    def artis(self) -> Arits:
        return Arits()

    @cached_property
    def translate(self) -> Translate:
        return Translate()

    async def img_stage0_process(self, index: dict[str, Any]) -> tuple[Any, Path] | None:
        folder = None
        try:
            folder, custom_community_name = await POSTFolderManager(index, self.input_community_name).create_folder()
            MainProcessor.created_folders.add(folder)
            MP = MainProcessor(index, folder, self.input_community_name, custom_community_name)
            if folder is None:
                logger.error(f"Failed to create folder for {MP.title}")
            else:
                return (MP, Path(folder))
        except Exception as e:
            logger.exception(f"Error in stage 0: {e}")
            return None

    async def img_stage1_process(
        self,
        index: dict[str, Any],
        MP: MainProcessor,
        folder: Path,
        handle_cancel: Callable[[Path | None], Awaitable[None]],
    ) -> tuple[MainProcessor, list[str], list[Path], Path] | None:
        try:
            async with semaphore:
                list_images = MP.parse_list_images(index)
                image_url_list, img_file_path_list = await MP.process_image(list_images)
                return (MP, image_url_list, img_file_path_list, folder)
        except asyncio.CancelledError:
            await handle_cancel(folder)
            return None
        except Exception as e:
            logger.exception(f"Error in img_stage1: {e}")
            return None

    async def img_stage2_request(self, MP: MainProcessor, image_url: str) -> bytes | None:
        try:
            response_bytes = await MP.request_image(image_url)
            return response_bytes
        except Exception as e:
            logger.exception(f"Error in stage 2: {e}")
            return None

    async def img_stage3_write(
        self,
        MP: MainProcessor,
        response_bytes: bytes,
        img_file_path: Path,
        folder: Path,
    ) -> Path | str:
        try:
            await MP.write_image_to_file(response_bytes, img_file_path)
            return folder
        except Exception as e:
            logger.exception(f"Error in stage 3: {e}")
            return "Failed"

    async def handle_cancel(self, folder: Path | None) -> None:
        try:
            if folder and Path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
                logger.info(f"Removed partial file: {folder}")
        except OSError as e:
            logger.warning(f"Failed to remove file {folder}: {e}")

    def filter_post_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """過濾貼文資料，將包含圖片的資料與不包含圖片的資料分開"""
        image_data, none_image_data = [], []
        for item in self.selected_media:
            image_info = item.get("imageInfo")
            if isinstance(image_info, tuple) and len(image_info[0]) > 0:
                image_data.append(item)
            else:
                none_image_data.append(item)
        return image_data, none_image_data

    async def process_item(self, item: dict[str, Any], has_images: bool) -> None:
        # Stage 0 Initialize processor and folder
        stage0_result = await self._stage0_init(item)
        if not stage0_result:
            return
        MP, folder = stage0_result
        await self._save_json(MP, folder)
        await self._process_html(MP, folder)
        # If image processing is required and noimages/nodl is not set proceed with image flow
        if has_images and not paramstore.get("noimages") and not paramstore.get("nodl"):
            await self._process_images(item, MP, folder)

    async def run_post_dl(self) -> None:
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}POST")
            return

        # Separate data into two categories with images and without images
        image_data, none_image_data = self.filter_post_data()

        tasks = []
        # Items with images
        for item in image_data:
            tasks.append(self.process_item(item, has_images=True))
        # Items without images
        for item in none_image_data:
            tasks.append(self.process_item(item, has_images=False))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _stage0_init(self, item: dict[str, Any]) -> tuple[Any, Path] | None:
        # Stage 0 Create folder and initialize MainProcessor
        return await self.img_stage0_process(item)

    async def _process_images(self, item: dict[str, Any], MP: Any, folder: Path) -> None:
        stage1_result = await self.img_stage1_process(item, MP, folder, self.handle_cancel)
        if not stage1_result:
            return
        MP, image_url_list, img_file_path_list, folder = stage1_result
        """image_url_list [[mediaid], [image_url], [1920,1080]]"""
        for url, img_path in zip(image_url_list[1], img_file_path_list):
            # Stage 2 Send request to get image bytes
            response_bytes = await self.img_stage2_request(MP, url)
            if response_bytes:
                # Stage 3 Write image file immediately
                await self.img_stage3_write(MP, response_bytes, img_path, folder)

    async def _process_html(self, MP: Any, folder: Path) -> None:
        await MP.process_html(folder)

    async def _save_json(self, MP: Any, folder: Path) -> None:
        await MP.save_json_file(folder)
