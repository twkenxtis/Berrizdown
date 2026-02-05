import asyncio
import os
import re
from urllib.parse import urljoin

import aiofiles
import m3u8

from berrizdown.static.color import Color
from berrizdown.lib.__init__ import use_proxy
from berrizdown.static.parameter import paramstore
from berrizdown.unit.http.request_berriz_api import GetRequest
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.lib.path import Path

logger = setup_logging("subdl", "peach")

TIMESTAMP_RE = re.compile(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}')
VIDEO_EXTENSIONS: set[str] = {'ts', 'avi', 'mp4', 'mkv', 'm4v', 'mov'}


class SaveSub:
    def __init__(self, output_dir: str, m3u8_content: str, video_file_name: str) -> None:
        if paramstore.get("nosubfolder") is True:
            self.output_dir: Path = Path(output_dir).parent.parent.parent
        else:
            self.output_dir: Path = Path(output_dir).parent
            
        self.m3u8_content: str = m3u8_content
        self.video_file_name: str = video_file_name
        self._request_client: GetRequest = GetRequest()
        self.subs_info: list[tuple[str, str, str]] = []
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(17)

    def parse_m3u8(self) -> list[tuple[str, str, str]]:
        try:
            playlist: m3u8.Playlist = m3u8.loads(self.m3u8_content)
            base_name: str = self._strip_extension()
            self.subs_info = [
                (
                    media.language,
                    media.uri,
                    os.path.join(self.output_dir, f"{base_name}_{media.language}.srt")
                )
                for media in playlist.media
                if media.type == 'SUBTITLES'
            ]
        except Exception as e:
            logger.error(f"Failed to parse M3U8: {e}")
        return self.subs_info

    def _strip_extension(self) -> str:
        name, ext = os.path.splitext(self.video_file_name)
        return name if ext.lstrip('.').lower() in VIDEO_EXTENSIONS else self.video_file_name

    async def _fetch(self, url: str) -> str:
        async with self._semaphore:
            try:
                return await self._request_client.get_request(url, use_proxy)
            except Exception as e:
                logger.error(f"Fetch error {url}: {e}")
                return None

    async def _download_segments(self, playlist_url: str, content: str) -> list[str]:
        try:
            playlist: m3u8.Playlist = m3u8.loads(content)
            
            urls = [
                urljoin(playlist_url, seg.uri) for seg in playlist.segments
            ]
            
            results = await asyncio.gather(
                *(self._fetch(u) for u in urls),
                return_exceptions=True
            )
            
            seen: set[str] = set()
            vtts: list[str] = []
            
            for r in results:
                if isinstance(r, Exception):
                    logger.warning(f"Segment download failed: {r}")
                    continue
                    
                if isinstance(r, str):
                    # 移除 BOM 並去除空白
                    r = r.lstrip('\ufeff').strip()
                    if r and r not in seen:
                        seen.add(r)
                        vtts.append(r)
                        
            return vtts
            
        except Exception as e:
            logger.error(f"Failed to download segments: {e}")
            return []

    def _vtt_to_srt(self, vtt: str) -> str:
        lines = vtt.splitlines()
        blocks: list[str] = []
        counter = 1
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 檢查是否為時間戳行
            if not TIMESTAMP_RE.match(line):
                i += 1
                continue
            
            timestamp = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', line)
            
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip() and not TIMESTAMP_RE.match(lines[i]):
                text_lines.append(lines[i].rstrip())
                i += 1
            
            # 組成 SRT 區塊
            if text_lines:
                blocks.append(f"{counter}\n{timestamp}\n{'\n'.join(text_lines)}\n")
                counter += 1
        
        return "\n".join(blocks).strip()

    async def _worker(self, lang: str, uri: str, srtfile: str) -> None:
        try:
            logger.info(f"{Color.fg('mist')}{lang} from {uri}{Color.reset()}")
            
            # 下載播放列表
            content: str = await self._fetch(uri)
            if not content:
                logger.warning(f"Failed to fetch playlist for {lang}")
                return

            # 下載所有片段
            vtts: list[str] = await self._download_segments(uri, content)
            if not vtts:
                logger.warning(f"No segments found for {lang}")
                return

            # 轉換並儲存
            srt = self._vtt_to_srt("\n\n".join(vtts))
            os.makedirs(os.path.dirname(srtfile), exist_ok=True)
            
            async with aiofiles.open(srtfile, "w", encoding="utf-8") as f:
                await f.write(srt)

            logger.info(
                f"{Color.fg('blue')}{lang} "
                f"{Color.fg('light_blue')}to "
                f"{Color.fg('light_gray')}{self.output_dir}{Color.reset()}"
            )
            
        except Exception as e:
            logger.error(f"Worker failed for {lang}: {e}")

    async def start(self) -> None:
        subs: list[tuple[str, str, str]] = self.parse_m3u8()
        if not subs:
            logger.info("No subtitles found in M3U8")
            return
        
        results = await asyncio.gather(
            *(self._worker(*s) for s in subs),
            return_exceptions=True
        )
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                lang = subs[i][0]
                logger.error(f"Subtitle {lang} processing failed: {result}")
