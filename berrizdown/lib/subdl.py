import asyncio
import os
import re
from typing import Optional
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
VIDEO_EXTENSIONS = {'ts', 'avi', 'mp4', 'mkv', 'm4v', 'mov'}


class SaveSub:
    def __init__(self, output_dir: str, m3u8_content: str, video_file_name: str):

        if paramstore.get("nosubfolder") is True:
            self.output_dir: Path = Path(output_dir).parent.parent.parent
        else:
            self.output_dir: Path = Path(output_dir).parent
            
        self.m3u8_content: str = m3u8_content
        self.video_file_name: str = video_file_name
        self._request_client: GetRequest = GetRequest()
        self.subs_info: list[tuple[str, str, str]] = []

    def parse_m3u8(self):
        try:
            playlist = m3u8.loads(self.m3u8_content)
            base_name = self._strip_extension()
            self.subs_info = [
                (media.language, media.uri,
                 os.path.join(self.output_dir, f"{base_name}_{media.language}.srt"))
                for media in playlist.media if media.type == 'SUBTITLES'
            ]
        except Exception as e:
            logger.error(f"Failed to parse M3U8: {e}")
        return self.subs_info

    def _strip_extension(self):
        name, ext = os.path.splitext(self.video_file_name)
        return name if ext[1:].lower() in VIDEO_EXTENSIONS else self.video_file_name

    async def _fetch(self, url: str) -> Optional[str]:
        try:
            return await self._request_client.get_request(url, use_proxy)
        except Exception as e:
            logger.error(f"Fetch error {url}: {e}")
            return None

    async def _download_segments(self, playlist_url: str, content: str):
        playlist = m3u8.loads(content)
        urls = [urljoin(playlist_url, seg.uri) for seg in playlist.segments]
        results = await asyncio.gather(*(self._fetch(u) for u in urls))
        seen, vtts = set(), []
        for r in results:
            if isinstance(r, str):
                r = r.lstrip('\ufeff').strip()
                if r and r not in seen:
                    seen.add(r)
                    vtts.append(r)
        return vtts

    def _vtt_to_srt(self, vtt: str) -> str:
        lines, blocks, counter = vtt.splitlines(), [], 1
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if TIMESTAMP_RE.match(line):
                ts = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', line)
                text = []
                i += 1
                while i < len(lines) and lines[i].strip() and not TIMESTAMP_RE.match(lines[i]):
                    text.append(lines[i].rstrip()); i += 1
                if text:
                    blocks.append(f"{counter}\n{ts}\n{'\n'.join(text)}\n")
                    counter += 1
            i += 1
        return "\n".join(blocks).strip()

    async def _worker(self, lang, uri, srtfile):
        logger.info(f"{Color.fg('mist')}{lang} from {uri}{Color.reset()}")
        content = await self._fetch(uri)
        if not content:
            return

        vtts = await self._download_segments(uri, content)
        if not vtts:
            return

        srt = self._vtt_to_srt("\n\n".join(vtts))
        os.makedirs(os.path.dirname(srtfile), exist_ok=True)
        async with aiofiles.open(srtfile, "w", encoding="utf-8") as f:
            await f.write(srt)

        logger.info(
            f"{Color.fg('blue')}{lang} "
            f"{Color.fg('light_blue')}to "
            f"{Color.fg('light_gray')}{self.output_dir}{Color.reset()}"
        )

    async def start(self):
        subs = self.parse_m3u8()
        if not subs: return
        await asyncio.gather(*(self._worker(*s) for s in subs))