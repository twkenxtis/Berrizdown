import asyncio
import html
import os
import re
from functools import cached_property
from urllib.parse import ParseResult, urlparse

from berrizdown.lib.__init__ import OutputFormatter
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.name_metadata import fmt_files, get_image_ext_basename, meta_name
from berrizdown.lib.path import Path
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.date.date import get_formatted_publish_date
from berrizdown.unit.handle.handle_board_from import NoticeINFOFetcher
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.image.class_ImageDownloader import ImageDownloader

logger = setup_logging("get_body_images", "cerulean")


# 允許的圖片副檔名集合 frozenset 確保不可變
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "svg",
        "bmp",
        "ico",
        "webp",
        "avif",
        "heic",
        "heif",
        "jxl",
        "jp2",
    }
)


BASE_URL_PREFIX: str = "https://statics.berriz.in/"


class Get_image_from_body:
    def __init__(self, html_content: str):
        self.html_content: str = html_content

    def is_valid_image_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url:
            return False
        # 快速檢查 URL 是否以指定網域開頭
        if not url.startswith(BASE_URL_PREFIX):
            return False
        # 解析 URL 獲取路徑
        parsed_url: ParseResult = urlparse(url)
        path: str = parsed_url.path
        # 使用 os.path.splitext 獲取副檔名
        url_path, ext_with_dot = os.path.splitext(path)
        # 移除 '.' 並轉為小寫，檢查是否在允許列表中
        extension: str = ext_with_dot[1:].lower() if ext_with_dot else ""
        return extension in IMAGE_EXTENSIONS

    def extract_image_urls_from_html(self) -> list[str]:
        # 正則表達式匹配 img 標籤的 src 屬性
        img_pattern: re.Pattern[str] = re.compile(r'<img[^>]+src="([^">]+)"', re.IGNORECASE)

        # 匹配 srcset 中的 URL（取第一個 URL）
        srcset_pattern: re.Pattern[str] = re.compile(r'<img[^>]+srcset="([^">]+)"', re.IGNORECASE)
        urls: list[str] = []
        # 提取普通 src 屬性
        for match in img_pattern.findall(self.html_content):
            # 解碼 HTML 實體（如 &amp; -> &）
            decoded_url: str = html.unescape(match)
            urls.append(decoded_url)

        # 提取 srcset 屬性中的 URL
        for srcset_match in srcset_pattern.findall(self.html_content):
            # srcset 格式: "image1.jpg 1x, image2.jpg 2x"
            srcset_content: str = html.unescape(srcset_match)
            # 取每個 URL（逗號分隔的第一部分）
            for srcset_item in srcset_content.split(","):
                url_part: str = srcset_item.strip().split()[0] if srcset_item.strip() else ""
                if url_part:
                    urls.append(url_part)
        return urls

    def find_valid_image_urls_in_file(self) -> list[str]:
        # 提取所有圖片 URL
        all_image_urls: list[str] = self.extract_image_urls_from_html()
        # 過濾有效的圖片 URL
        valid_urls: list[str] = [url for url in all_image_urls if self.is_valid_image_url(url)]
        return valid_urls


class DownloadImage(Get_image_from_body):
    def __init__(
        self,
        html_content: str,
        folder_path: Path,
        fetcher: NoticeINFOFetcher,
        community_name: str,
        custom_community_name: str,
        input_community_name: str,
    ):
        super().__init__(html_content)
        self.all_image_urls: list[str] = self.find_valid_image_urls_in_file()
        self.folderpath: Path = folder_path
        self.ImageDownloader: ImageDownloader = ImageDownloader()
        self.fetcher: NoticeINFOFetcher = fetcher
        self.community_name: str = community_name or input_community_name
        self.custom_community_name: str = custom_community_name or input_community_name

    @cached_property
    def title(self) -> str:
        return self.fetcher.get_title()

    @cached_property
    def save_title(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.title)

    @cached_property
    def reservedAt(self) -> str:
        return self.fetcher.get_reservedAt()

    @cached_property
    def time_str(self) -> str:
        return get_formatted_publish_date(self.reservedAt, fmt_files)

    async def start_download_images(self) -> list[Path]:
        """Download all images concurrently, write to disk, and return list of file paths."""
        if not self.all_image_urls:
            return []
        # Download all images concurrently get bytes
        download_tasks: list[asyncio.Task] = [asyncio.create_task(self.ImageDownloader.download_image(url=url)) for url in self.all_image_urls]
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        # Write downloaded bytes to files concurrently
        write_tasks: list[asyncio.Task] = []
        file_paths: list[Path] = []

        for idx, result in enumerate(download_results):
            if isinstance(result, bytes):
                file_path = self._generate_filepath(self.all_image_urls[idx])
                file_paths.append(file_path)
                write_tasks.append(asyncio.create_task(self.ImageDownloader._write_to_file(result, file_path)))
            elif isinstance(result, Exception):
                logger.error(f"Failed to download {self.all_image_urls[idx]}: {result}")

        # Wait for all write operations to complete
        write_results = await asyncio.gather(*write_tasks, return_exceptions=True)

        # Filter successful writes
        successful_paths: list[Path] = [file_paths[idx] for idx, result in enumerate(write_results) if not isinstance(result, Exception)]
        return successful_paths

    def _generate_filepath(self, url: str) -> Path:
        """Generate safe file path from URL."""
        # Extract filename from URL
        image_name: str = self.image_name(url)
        return self.folderpath / image_name

    def image_name(self, image_url: str):
        base_name, ext = get_image_ext_basename(image_url)
        iamge_meta: dict = meta_name(
            self.time_str,
            self.fetcher.get_title(),
            self.community_name,
            self.custom_community_name,
        )
        iamge_meta["raw_name"] = base_name
        image_file_name: str = OutputFormatter(f"{CFG['output_template']['image_file_name']}").format(iamge_meta)
        output_image_name: str = f"{image_file_name}{ext}"
        return output_image_name
