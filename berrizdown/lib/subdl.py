import asyncio
import os
import re
from typing import Any
from urllib.parse import urljoin

import aiofiles
import m3u8

from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.lib.__init__ import (
    resolve_conflict_path,
    printer_video_folder_path_info,
    use_proxy
)
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.path import Path
from berrizdown.unit.http.request_berriz_api import GetRequest
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("subdl", "peach")

TIMESTAMP_RE = re.compile(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}')
VIDEO_EXTENSIONS: set[str] = {'ts', 'avi', 'mp4', 'mkv', 'm4v', 'mov'}


class SaveSub:
    def __init__(self, output_dir: Path, m3u8_content: str, sub_file_name: str) -> None:
        if paramstore.get("nosubfolder") is True and paramstore.get("subs_only") is None:
            self.output_dir: Path = output_dir.parent.parent.parent
        elif paramstore.get("subs_only") is True:
            self.output_dir: Path = output_dir
        else:
            self.output_dir: Path = output_dir.parent
            
        self.m3u8_content: str = m3u8_content
        self.sub_file_name: str = sub_file_name
        self._request_client: GetRequest = GetRequest()
        self.subs_info: list[tuple[str, str, str]] = []
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(51)

    async def parse_m3u8(self) -> list[tuple[str, str, str]]:
        try:
            playlist: m3u8.Playlist = m3u8.loads(self.m3u8_content)
            subtitles: list[m3u8.Media] = [m for m in playlist.media if m.type == 'SUBTITLES']
            
            tasks = [
                asyncio.create_task(
                    resolve_conflict_path(
                        os.path.join(self.output_dir, f"{self.sub_file_name}.{m.language}.srt")
                    )
                )
                for m in subtitles
            ]
            
            paths = await asyncio.gather(*tasks)
            
            self.subs_info: list[tuple[str, str, str]] = [
                (m.language, m.uri, path)
                for m, path in zip(subtitles, paths)
            ]
        except Exception as e:
            logger.error(f"Failed to parse M3U8: {e}")
        return self.subs_info


    async def _fetch(self, url: str) -> str:
        async with self._semaphore:
            try:
                return await self._request_client.get_request(url, use_proxy)
            except Exception as e:
                logger.error(f"Fetch error {url}: {e}")
                return None

    def build_segment_urls(self, playlist_url: str, playlist: m3u8.Playlist) -> list[str]:
        return [urljoin(playlist_url, seg.uri) for seg in playlist.segments]

    async def fetch_all_segments(self, urls: list[str]) -> list[str]:
        tasks = [asyncio.create_task(self._fetch(url)) for url in urls]
        results: list[str] = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def deduplicate_segments(self, results: list[str]) -> list[str]:
        """去重並清理片段內容"""
        seen: set[str] = set()
        vtts: list[str] = []
        
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Segment download failed: {r}")
                continue
                
            if isinstance(r, str):
                r = r.lstrip('\ufeff').strip()
                if r and r not in seen:
                    seen.add(r)
                    vtts.append(r)
        return vtts

    async def download_segments(self, playlist_url: str, content: str) -> list[str]:
        try:
            playlist: m3u8.Playlist = m3u8.loads(content)
            urls: list[str] = self.build_segment_urls(playlist_url, playlist)
            results: list[str] = await self.fetch_all_segments(urls)
            vtts: list[str] = self.deduplicate_segments(results)
            return vtts
        except Exception as e:
            logger.error(f"Failed to download segments: {e}")
            return []

    def parse_subtitle_block(self, lines: list[str], i: int) -> tuple[int, str, list[str]]:
        """解析單個字幕區塊 返回新位置 時間戳和文本行"""
        line = lines[i].strip()
        
        if not TIMESTAMP_RE.match(line):
            return i + 1, None, []
        
        timestamp = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', line)
        i += 1
        
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not TIMESTAMP_RE.match(lines[i]):
            text_lines.append(lines[i].rstrip())
            i += 1
        
        return i, timestamp, text_lines

    def vtt_to_srt(self, vtt: str) -> str:
        lines = vtt.splitlines()
        blocks: list[str] = []
        counter = 1
        i = 0
        
        while i < len(lines):
            i, timestamp, text_lines = self.parse_subtitle_block(lines, i)
            
            if timestamp and text_lines:
                blocks.append(f"{counter}\n{timestamp}\n{'\n'.join(text_lines)}\n")
                counter += 1
        
        return "\n".join(blocks).strip()

    async def fetch_playlist_content(self, uri: str, lang: str = "") -> str:
        content: str = await self._fetch(uri)
        if not content:
            logger.warning(f"Failed to fetch playlist for {lang} from {uri}")
        return content

    async def _process_segments_to_srt(self, vtts: list[str]) -> str:
        if not vtts:
            logger.warning(f"No segments found")
            return None
        return self.vtt_to_srt("\n\n".join(vtts))

    async def save_subtitle_file(self, srtfile: str, srt: str) -> None:
        async with aiofiles.open(srtfile, "w", encoding="utf-8") as f:
            await f.write(srt)

    async def process_subtitle_task(self, lang: str, uri: str, srtfile: str) -> None:
        try:
            content: str = await self.fetch_playlist_content(uri)
            if not content:
                return
            
            vtts: list[str] = await self.download_segments(uri, content)
            srt: str = await self._process_segments_to_srt(vtts)
            if not srt:
                return
            
            await self.save_subtitle_file(srtfile, srt)
            self.print_subtitle_save_path(lang, srtfile)
        except Exception as e:
            logger.error(f"Subtitle task failed for {lang}: {e}")
            
    def print_subtitle_save_path(self, lang: str, srtfile: Path):
        printer_video_folder_path_info(
            srtfile, srtfile.name, \
                f'{Color.fg("royal_blue")}Subtitle {Color.fg("light_slate_gray")}<{lang}>{Color.reset()} '
        )

    async def start(self) -> list[tuple[str, str, Path]]|list:
        subs: list[tuple[str, str, str]] = await self.parse_m3u8()
        if not subs:
            logger.info("No subtitles found in M3U8")
            return
        
        results: list[Any] = await asyncio.gather(
            *(self.process_subtitle_task(*s) for s in subs),
            return_exceptions=True
        )
        
        successful: list[tuple[str, str, Path]]|list = []
        for s, r in zip(subs, results):
            if isinstance(r, Exception):
                logger.error(f"Subtitle {s[0]} processing failed: {r}")
            else:
                successful.append(s)  # only susscessful results
        
        return successful