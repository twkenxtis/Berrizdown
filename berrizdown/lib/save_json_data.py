import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import Any
from urllib.parse import urlparse

import aiofiles
import httpx
import orjson

from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.PlaybackInfo import PlaybackInfo
from berrizdown.static.PublicInfo import PublicInfo
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import GetRequest
from berrizdown.lib.__init__ import (
    File_date_time_formact,
    OutputFormatter,
    get_artis_list,
    printer_video_folder_path_info,
    resolve_conflict_path,
    use_proxy,
)
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.path import Path

logger = setup_logging("save_json_data", "peach")


class save_json_data:
    def __init__(
        self,
        output_dir: str | Path,
        custom_community_name: str,
        community_name: str,
        public_info: PublicInfo | None = None,
        playback_info: PlaybackInfo | None = None,
    ) -> None:
        self.output_dir: Path = Path(output_dir).resolve()
        self.info_path: Path = self.output_dir.parent
        self.max_retries: int = 3
        self.retry_delay: int = 2
        self.executor = ThreadPoolExecutor()

        self.custom_community_name: str = custom_community_name or community_name
        self.community_name: str = community_name
        self.public_info: PublicInfo | None = public_info
        self.playback_info: PlaybackInfo | None = playback_info

        if public_info is not None:
            self.artis_list: list[dict[str, str | None]] = public_info.artists

    @cached_property
    def FDT(self) -> File_date_time_formact:
        return File_date_time_formact(self.public_info, "VOD_LIVE")

    @cached_property
    def time_str(self) -> str:
        return self.FDT.vod_live_time_str()

    @cached_property
    def title(self) -> str:
        return FilenameSanitizer.sanitize_filename(self.public_info.title)

    @cached_property
    def get_artis(self) -> str:
        return get_artis_list(self.artis_list)

    @cached_property
    def artis_name(self) -> str:
        return self.get_artis.lower() if self.get_artis == self.community_name else self.get_artis

    def close(self) -> None:
        self.executor.shutdown(wait=True)

    async def _write_file(self, file_path: Path, content: str | bytes) -> None:
        """Write content to a file with retry logic using aiofiles."""
        mode = "w" if isinstance(content, str) else "wb"
        is_text_mode: bool = "b" not in mode

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create parent directory for {file_path}: {e}")
        resolve_file_path = await resolve_conflict_path(file_path)
        if is_text_mode and isinstance(content, bytes):
            content = content.decode("utf-8")
        elif not is_text_mode and isinstance(content, str):
            content = content.encode("utf-8")

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Writing to {Color.fg('mist')}{resolve_file_path}{Color.reset()}")
                if is_text_mode:
                    async with aiofiles.open(resolve_file_path, mode=mode, encoding="utf-8") as f:
                        await f.write(content)
                else:
                    async with aiofiles.open(resolve_file_path, mode=mode) as f:
                        await f.write(content)
                return
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {resolve_file_path}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise RuntimeError(f"Failed to write to {resolve_file_path} after {self.max_retries} attempts: {e}")

    def play_list_meta(self, FORMACT: str) -> tuple[str, Path]:
        playlist_meta: dict[str, str] = {
            "date": self.time_str,
            "title": self.title,
            "artis": self.artis_name,
            "community_name": self.community_name,
            "source": "Berriz",
            "tag": CFG["output_template"]["tag"],
        }
        name: str = OutputFormatter(f"{FORMACT}").format(playlist_meta)
        if paramstore.get("nosubfolder") is True:
            meta_data_path = self.info_path.parent.parent
        else:
            meta_data_path = self.info_path
        return name, meta_data_path

    async def mpd_to_folder(self, raw_mpd: httpx.Response) -> None:
        """Save MPD content (expecting an object with a .text attribute) to manifest.mpd"""
        match paramstore.get("noplaylist"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip save{Color.reset()} {Color.fg('light_gray')}mpd playlist file")
            case _:
                mpd_file_name, meta_data_path = self.play_list_meta(CFG["output_template"]["playlist_file_name"])
                if raw_mpd is None:
                    return
                try:
                    if paramstore.get("nosubfolder") is True:
                        self.output_dir = self.output_dir.parent
                    content: str = raw_mpd
                    await self._write_file(meta_data_path / f"{mpd_file_name}.mpd", content)
                    self.put_console_output(
                        meta_data_path / f"{mpd_file_name}.mpd",
                        f"{mpd_file_name}.mpd",
                        f"{Color.fg('light_blue')}MPD{Color.reset()}",
                    )
                except AttributeError as e:
                    raise ValueError("Failed to save MPD playlist") from e

    async def hls_to_folder(self, raw_hls: str) -> None:
        """Save HLS content to manifest.m3u8"""
        match paramstore.get("noplaylist"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip save{Color.reset()} {Color.fg('light_gray')}m3u8 playlist file")
            case _:
                hls_file_name, meta_data_path = self.play_list_meta(CFG["output_template"]["playlist_file_name"])
                if raw_hls is None:
                    return
                content: str = raw_hls
                await self._write_file(meta_data_path / f"{hls_file_name}.m3u8", content)
                self.put_console_output(
                    meta_data_path / f"{hls_file_name}.m3u8",
                    f"{hls_file_name}.m3u8",
                    f"{Color.fg('magenta_pink')}M3U8{Color.reset()}",
                )

    async def play_list_to_folder(self, raw_play_list: object) -> None:
        """Save playlist JSON to meta.json"""
        match paramstore.get("nojson"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}Video metadata JSON")
            case _:
                if raw_play_list is None:
                    return
                try:
                    json_bytes: bytes = orjson.dumps(raw_play_list, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
                    json_file_name, meta_data_path = self.play_list_meta(CFG["output_template"]["json_file_name"])
                    await self._write_file(meta_data_path / f"{json_file_name}_meta.json", json_bytes)
                    self.put_console_output(
                        meta_data_path / f"{json_file_name}_meta.json",
                        f"{json_file_name}_meta.json",
                        f"{Color.fg('blush')}META Json{Color.reset()}",
                    )
                except orjson.JSONEncodeError as e:
                    if paramstore.get("mpd_video") is True:
                        raise ValueError("Failed to serialize playlist to JSON") from e

    async def json_data_to_folder(self) -> None:
        """將 JSON 資料儲存到下載資料夾中"""
        match paramstore.get("nojson"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}Video INFO JSON")
            case _:
                json_data: tuple[dict[str, Any]] = (self.str2orjson_dict(),)
                serialized: bytes = orjson.dumps(
                    json_data,
                    option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
                )
                json_file_name, meta_data_path = self.play_list_meta(CFG["output_template"]["json_file_name"])
                await self._write_file(meta_data_path / f"{json_file_name}_info.json", serialized)
                self.put_console_output(
                    meta_data_path / f"{json_file_name}_info.json",
                    f"{json_file_name}_info.json",
                    f"{Color.fg('yellow_ochre')}INFO Json{Color.reset()}",
                )

    async def dl_thumbnail(self) -> None:
        """下載影片縮圖到上級目錄"""
        match paramstore.get("nothumbnails"):
            case True:
                logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()} {Color.fg('light_gray')}Vido Thumbnails")
            case _:
                thumbnail_url: str | None = self.public_info.thumbnail_url
                if not thumbnail_url:
                    logger.warning("No thumbnail URL found")
                    return
                response: httpx.Response = await GetRequest().get_request(thumbnail_url, use_proxy)
                thumbnail_url
                thumbnail_file_name, meta_data_path = self.play_list_meta(CFG["output_template"]["image_file_name"])
                output_thumbnail_name: str = f"{thumbnail_file_name}_Thumbnail"
                ext = Path(urlparse(thumbnail_url).path).suffix
                temp_path: Path = await resolve_conflict_path(meta_data_path / f"{output_thumbnail_name}{ext}")
                save_path: Path = temp_path.with_suffix(ext)
                try:
                    content: bytes = response
                    async with aiofiles.open(save_path, "wb") as f:
                        await f.write(content)
                    self.put_console_output(
                        save_path,
                        output_thumbnail_name,
                        f"{Color.fg('light_mint')}Thumbnail{Color.reset()}",
                    )
                except Exception as e:
                    logger.error(f"Thumbnail download failed: {e}")
                    raise RuntimeError("Thumbnail download failed") from e

    def str2orjson_dict(self) -> tuple[dict[str, Any]]:
        json_data: dict[str, Any] = {}
        public_dict: dict[str] = orjson.loads(self.playback_info.to_json())
        playback_dict: dict[str] = orjson.loads(self.playback_info.to_json())
        json_data = public_dict | playback_dict
        return json_data
    
    def sub_meta(self) -> str:
        sub_meta: dict[str, str] = {
            "date": self.time_str,
            "title": self.title,
            "artis": self.artis_name,
            "community_name": self.community_name,
            "source": "Berriz",
            "tag": CFG["output_template"]["tag"],
        }
        name: str = OutputFormatter(CFG["output_template"]["subtitle_file_name"]).format(sub_meta)
        return name
    
    def put_console_output(self, new_path: Path, file_name: str, TAG: str) -> None:
        printer_video_folder_path_info(new_path, file_name, f"{TAG} ")
