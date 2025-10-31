import asyncio
from functools import cached_property
from typing import Any

import aiofiles
import orjson
from lib.__init__ import printer_video_folder_path_info, resolve_conflict_path
from lib.path import Path
from static.color import Color
from static.parameter import paramstore
from unit.__init__ import FilenameSanitizer
from unit.handle.handle_board_from import JsonBuilder
from unit.handle.handle_log import setup_logging

logger = setup_logging("PostJsonDate", "dark_gray")


class PostJsonData:
    def __init__(self, index: dict, postid: int, new_file_name: str, community_name: str | None):
        self.community_name: str | None = community_name
        self.index: dict = index
        self.postid: int = postid
        self.new_file_name: str = new_file_name

        if self.community_name is None:
            raise ValueError("Community name is not provided.")

    @cached_property
    def json_builder(self):
        return JsonBuilder(self.index, self.postid)

    async def get_json_data(self) -> dict[str, Any]:
        data: dict[str, Any] = await self.json_builder.build_translated_json()
        data["link"] = f"https://berriz.in/en/{self.community_name}/board/{self.index['boardInfo']['boardId']}/post/{self.index['post']['postId']}"
        return data

    async def save_json_file_to_folder(self, file_path: Path) -> Path | None:
        if paramstore.get("nojson") is True:
            return None
        self.new_file_name = FilenameSanitizer.sanitize_filename(self.new_file_name)
        json_path: Path = await resolve_conflict_path(Path.cwd() / file_path / f"{self.new_file_name}.json")
        if not file_path.exists():
            try:
                file_path.mkdirp()
            except Exception as e:
                logger.error(f"Failed to create directory {file_path}: {e}")
                return None
        printer_video_folder_path_info(json_path, json_path.name, f"{Color.fg('blue')}Json {Color.reset()}")
        try:
            json_data: dict[str, Any] = await self.get_json_data()
            if not isinstance(json_data, dict):
                raise TypeError("JSON data received is not a dictionary.")
            json_bytes: bytes = await asyncio.to_thread(orjson.dumps, json_data, option=orjson.OPT_INDENT_2)
            async with aiofiles.open(json_path, "wb") as f:
                await f.write(json_bytes)
            logger.debug(f"Saved JSON successfully to {json_path}")
            return json_path
        except Exception as e:
            logger.error(f"Failed to save JSON to {json_path}: {e}")
            return None
