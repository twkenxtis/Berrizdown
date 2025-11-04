import asyncio
from functools import lru_cache
from typing import TypeAlias

import aiofiles
from bs4 import BeautifulSoup, Tag
from bs4.element import Tag

from berrizdown.lib.__init__ import printer_video_folder_path_info, resolve_conflict_path
from berrizdown.lib.path import Path
from berrizdown.static.color import Color
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("save_html", "magenta_pink")
URL: TypeAlias = str


@lru_cache(maxsize=1)
def open_template_post_html() -> str:
    try:
        htmlpath: Path = Path(Path.cwd() / "berrizdown" / "unit" / "post" / "template.html")
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
        artis: str,
        folder_path: Path,
        artis_avator: URL,
        file_name: str,
        input_board_name: str,
        html_file: str,
    ) -> None:
        self.title: str = title
        self.time: str = time
        self.body: str = body
        self.artis: str = artis
        self.artis_a: str = artis_avator
        self.safe_title: str = FilenameSanitizer.sanitize_filename(title)
        self.folder: Path = folder_path
        self.soap: Tag | None = None
        self.file_name: str = file_name
        self.input_board_name: str = input_board_name
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

    async def artis_p(self) -> None:
        # 尋找藝人標籤
        artis_p: Tag | None = self.soup.find("p", class_="f-body-s-medium text-GRAY002 line-clamp-1 break-all")
        # 更新標題標籤
        if artis_p:
            artis_p.clear()
            artis_p.string = self.artis
        else:
            logger.error('Cant find <p class="f-body-s-medium text-GRAY002 line-clamp-1 break-all')

    async def board_name(self) -> None:
        # 尋找藝人標籤
        board_h1: Tag | None = self.soup.find("h1", class_="f-body-l-semibold text-GRAY400")
        # 更新標題標籤
        if board_h1:
            board_h1.clear()
            board_h1.string = self.input_board_name
        else:
            logger.error('Cant find <p class="f-body-s-medium text-GRAY002 line-clamp-1 break-all')

    async def artis_avator(self) -> None:
        """
        尋找完全匹配固定 URL 的 <img>，並替換成 self.artis_a
        """
        FIXED_URL = "https://statics.berriz.in/cdn/community_artist/image/PUT_BERRIZ_ARTIS_AVATAR_URL.jpg"

        # 找到 <img src="FIXED_URL">
        artis_a: Tag | None = self.soup.find("img", {"src": FIXED_URL})

        if artis_a:
            # 直接替換 src 屬性
            artis_a["src"] = self.artis_a
        else:
            logger.error(f"Can't find <img src='{FIXED_URL}'>")

    async def write_html_file(self) -> None:
        html_path: Path = await resolve_conflict_path(Path.cwd() / Path(self.folder) / f"{self.file_name}.html")
        # 寫回檔案
        async with aiofiles.open(html_path, "w", encoding="utf-8") as file:
            await file.write(str(self.soup))
            printer_video_folder_path_info(
                html_path,
                html_path.name,
                f"{Color.fg('midnight_blue')}POST {Color.fg('orchid')}HTML {Color.reset()}",
            )

    async def update_template_file(self) -> None:
        """
        讀取 template.html，更新指定標籤的內容，並使用 TaskGroup 寫回檔案
        """
        content: str = self.html
        self.soup: BeautifulSoup = BeautifulSoup(content, "html.parser")
        await asyncio.gather(
            self.time_div(),
            self.div_content(),
            self.artis_p(),
            self.artis_avator(),
            self.board_name(),
        )
        await self.write_html_file()
