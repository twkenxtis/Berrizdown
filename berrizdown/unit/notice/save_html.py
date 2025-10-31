import asyncio
from functools import lru_cache

import aiofiles
from bs4 import BeautifulSoup, Tag
from lib.__init__ import printer_video_folder_path_info, resolve_conflict_path
from lib.path import Path
from static.color import Color
from unit.__init__ import FilenameSanitizer
from unit.handle.handle_log import setup_logging

logger = setup_logging("save_html", "flamingo_pink")


@lru_cache(maxsize=1)
def open_template_post_html() -> str:
    try:
        htmlpath: Path = Path(Path.cwd() / "berrizdown" / "unit" / "notice" / "template.html")
        with open(htmlpath, encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logger.error("Error: template.html file not found")
        raise FileNotFoundError


class SaveHTML:
    def __init__(
        self,
        title: str,
        time: str,
        body: str,
        folder_path: Path,
        file_name: str,
        html_file: str,
    ) -> None:
        self.title: str = title
        self.time: str = time
        self.body: str = body
        self.safe_title: str = FilenameSanitizer.sanitize_filename(title)
        self.folder: Path = folder_path
        self.soap: BeautifulSoup | None = None
        self.file_name = file_name
        self.html: str = html_file

    async def div_content(self) -> None:
        # 尋找目標 div (主要內容)
        target_div_content: Tag | None = self.soup.find("div", class_="whitespace-pre-wrap break-words")
        # 更新主要內容
        if target_div_content:
            target_div_content.clear()
            target_div_content.append(BeautifulSoup(self.body, "html.parser"))
        else:
            logger.error("Cant find <div class='whitespace-pre-wrap break-words'>")
            return

    async def time_div(self) -> None:
        # 尋找時間標籤
        time_div: Tag | None = self.soup.find("div", class_="f-body-s-regular text-GRAY400 flex")
        # 更新時間標籤
        if time_div:
            time_div.clear()
            # 格式化時間顯示 (2025.09.24)
            formatted_time: str = f"{self.time[:4]}.{self.time[5:7]}.{self.time[8:10]}"
            time_tag: Tag = self.soup.new_tag("time", datetime=self.time)
            time_tag.string = formatted_time
            time_div.append(time_tag)
        else:
            logger.error("Cant find <div class='f-body-s-regular text-GRAY400 flex'>")

    async def title_p(self) -> None:
        # 尋找標題標籤
        title_p = self.soup.find(
            "p",
            attrs={
                "class": [
                    "text-GRAY002",
                    "break-all",
                    "f-body-xxl-semibold",
                    "line-clamp-3",
                ]
            },
        )
        # 更新標題標籤
        if title_p:
            title_p.clear()
            title_p.string = self.title
        else:
            logger.error("Cant find <p class='text-GRAY002 break-all f-body-xxl-semibold line-clamp-3'>")

    async def write_html_file(self) -> None:
        htmlpath: Path = await resolve_conflict_path(Path(self.folder / f"{self.file_name}.html"))
        # 寫回檔案
        async with aiofiles.open(htmlpath, "w", encoding="utf-8") as file:
            await file.write(str(self.soup))
            printer_video_folder_path_info(
                htmlpath,
                htmlpath.name,
                f"{Color.fg('periwinkle')}Notice {Color.fg('orchid')}HTML {Color.reset()}",
            )

    async def update_template_file(self) -> None:
        """
        讀取 template.html，更新指定標籤的內容，並使用 TaskGroup 寫回檔案
        """
        try:
            content: str = self.html
            self.soup: BeautifulSoup = BeautifulSoup(content, "html.parser")
            await asyncio.gather(self.title_p(), self.time_div(), self.div_content())
            return await self.write_html_file()
        except Exception as e:
            logger.error(f"{e}")
