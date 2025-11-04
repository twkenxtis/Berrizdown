import asyncio
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from berrizdown.lib.__init__ import use_proxy
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import GetRequest

logger = setup_logging("parse_hls", "periwinkle")

REGEX_HLS_PATTERN: str = r"#.*|.*\.(?:ts|mp4|m4a|m4v|aac)"


@dataclass
class HLSSegment:
    url: str
    duration: float
    sequence: int


@dataclass
class HLSVariant:
    """表示一個 HLS 視訊變體（特定解析度/bitrate）"""

    bandwidth: int
    resolution: tuple[int, int] | None
    codecs: str | None
    playlist_url: str
    frame_rate: float | None = None
    average_bandwidth: int | None = None
    segments: list[HLSSegment] = field(default_factory=list)

    segment_urls: list[str] = field(default_factory=list)
    init_url: str | None = None
    segment_template: str | None = None
    initialization_url: str | None = None
    mime_type: str = "video/mp2t"
    timescale: int = 1
    id: str | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self):
        if self.segments and not self.segment_urls:
            self.segment_urls = [seg.url for seg in self.segments]
        if not self.init_url:
            self.init_url = self.playlist_url
        if not self.initialization_url:
            self.initialization_url = self.init_url
        if self.resolution and not self.width and not self.height:
            self.width, self.height = self.resolution
        if not self.id:
            self.id = f"hls_video_{self.bandwidth}"


@dataclass
class HLSAudioTrack:
    """表示一個 HLS 音訊軌道"""

    name: str
    language: str | None
    uri: str
    bandwidth: int | None = None
    codecs: str | None = None
    channels: str | None = None
    segments: list[HLSSegment] = field(default_factory=list)

    segment_urls: list[str] = field(default_factory=list)
    init_url: str | None = None
    segment_template: str | None = None
    initialization_url: str | None = None
    mime_type: str = "audio/mp2t"
    timescale: int = 1
    id: str | None = None
    audio_sampling_rate: int | None = 48000
    width: int | None = None
    height: int | None = None

    def __post_init__(self):
        if self.segments and not self.segment_urls:
            self.segment_urls = [seg.url for seg in self.segments]
        if not self.init_url:
            self.init_url = self.uri
        if not self.initialization_url:
            self.initialization_url = self.init_url
        if not self.id:
            self.id = f"hls_audio_{self.name}"


@dataclass
class HLSMediaPlaylist:
    """表示解析後的媒體播放列表"""

    segments: list[HLSSegment]
    is_encrypted: bool
    encryption_key_uri: str | None
    encryption_key: bytes | None
    total_duration: float


@dataclass
class HLSContent:
    """包含解析後的所有 HLS 內容"""

    video_variants: list[HLSVariant]
    audio_tracks: list[HLSAudioTrack]
    base_url: str
    is_master_playlist: bool


class Codec:
    @staticmethod
    def match_codec(codec: str) -> str:
        if codec.startswith("avc1") or codec in ["avc", "avc1", "h264", "h.264"]:
            return "avc1"
        return codec


class HLSParser:
    """HLS 播放列表解析器"""

    PATTERNS = {
        "bandwidth": r"BANDWIDTH=(\d+)",
        "resolution": r"RESOLUTION=(\d+)x(\d+)",
        "codecs": r'CODECS="([^"]+)"',
        "frame_rate": r"FRAME-RATE=([\d.]+)",
        "avg_bandwidth": r"AVERAGE-BANDWIDTH=(\d+)",
        "name": r'NAME="([^"]+)"',
        "language": r'LANGUAGE="([^"]+)"',
        "uri": r'URI="([^"]+)"',
        "channels": r'CHANNELS="([^"]+)"',
        "duration": r"^#EXTINF:([\d.]+)",
    }

    def __init__(self):
        self.get_request = GetRequest()

    @staticmethod
    def _preprocess_content(content: str) -> list[str]:
        """預處理 M3U8 內容為行列表"""
        return [line.strip() for line in content.splitlines() if line.strip()]

    @staticmethod
    def _check_master_playlist(lines: list[str]) -> bool:
        """判斷是否為 master playlist"""
        return any(line.startswith("#EXT-X-STREAM-INF:") for line in lines)

    def _extract_attributes(self, line: str, patterns: dict[str, str]) -> dict[str, Any]:
        """統一的屬性擷取方法"""
        attrs = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                attrs[key] = match.groups() if len(match.groups()) > 1 else match.group(1)
        return attrs

    async def _fetch_segments_safe(self, url: str, track_type: str, track_id: str) -> list[HLSSegment]:
        """安全取得 segments"""
        try:
            media_playlist = await self.parse_media_playlist(url)
            return media_playlist.segments
        except Exception as e:
            logger.warning(f"Failed to fetch segments for {track_type} {url}: {e}")
            return []

    async def parse_playlist(self, m3u8_content_str: str, m3u8_url: str, fetch_segments: bool = True) -> HLSContent:
        """解析 M3U8 播放清單並傳回所有內容"""
        lines = self._preprocess_content(m3u8_content_str)
        base_url = m3u8_url.rsplit("/", 1)[0] + "/"

        if self._check_master_playlist(lines):
            video_variants = await self._parse_all_video_variants(lines, m3u8_url, fetch_segments)
            audio_tracks = await self._parse_all_audio_tracks(lines, m3u8_url, fetch_segments)

            return HLSContent(
                video_variants=video_variants,
                audio_tracks=audio_tracks,
                base_url=base_url,
                is_master_playlist=True,
            )
        else:
            logger.warning("Direct media playlist detected")
            media_playlist = await self.parse_media_playlist(m3u8_url)

            default_variant = HLSVariant(
                bandwidth=0,
                resolution=None,
                codecs=None,
                playlist_url=m3u8_url,
                segments=media_playlist.segments if fetch_segments else [],
            )

            return HLSContent(
                video_variants=[default_variant],
                audio_tracks=[],
                base_url=base_url,
                is_master_playlist=False,
            )

    async def _parse_all_video_variants(self, lines: list[str], m3u8_url: str, fetch_segments: bool = True) -> list[HLSVariant]:
        """解析所有視訊變體"""
        variants = []

        i = 0
        while i < len(lines):
            if lines[i].startswith("#EXT-X-STREAM-INF:"):
                variant = await self._parse_single_variant(lines, i, m3u8_url, fetch_segments)
                if variant:
                    variants.append(variant)
            i += 1

        return sorted(variants, key=lambda v: v.bandwidth)

    async def _parse_single_variant(self, lines: list[str], index: int, m3u8_url: str, fetch_segments: bool) -> HLSVariant | None:
        """解析單一視訊變體"""
        line = lines[index]

        attrs = self._extract_attributes(
            line,
            {
                "bandwidth": self.PATTERNS["bandwidth"],
                "resolution": self.PATTERNS["resolution"],
                "codecs": self.PATTERNS["codecs"],
                "frame_rate": self.PATTERNS["frame_rate"],
                "avg_bandwidth": self.PATTERNS["avg_bandwidth"],
            },
        )

        # 取得 playlist URL
        if index + 1 >= len(lines) or lines[index + 1].startswith("#"):
            return None

        playlist_url = urljoin(m3u8_url, lines[index + 1])

        # 解析屬性
        bandwidth = int(attrs.get("bandwidth", 0))
        resolution = None
        if "resolution" in attrs:
            w, h = attrs["resolution"]
            resolution = (int(w), int(h))

        codecs = attrs.get("codecs")
        frame_rate = float(attrs["frame_rate"]) if "frame_rate" in attrs else None
        avg_bandwidth = int(attrs["avg_bandwidth"]) if "avg_bandwidth" in attrs else None

        # 取得 segments
        segments = []
        if fetch_segments:
            segments = await self._fetch_segments_safe(playlist_url, "variant", f"{resolution} @ {bandwidth // 1000}kbps")

        return HLSVariant(
            bandwidth=bandwidth,
            resolution=resolution,
            codecs=codecs,
            playlist_url=playlist_url,
            frame_rate=frame_rate,
            average_bandwidth=avg_bandwidth,
            segments=segments,
        )

    async def _parse_all_audio_tracks(self, lines: list[str], m3u8_url: str, fetch_segments: bool = True):
        """解析所有音訊軌道"""
        audio_tracks = []

        for line in lines:
            if line.startswith("#EXT-X-MEDIA:") and "TYPE=AUDIO" in line:
                track = await self._parse_single_audio_track(line, m3u8_url, fetch_segments)
                if track:
                    audio_tracks.append(track)

        return audio_tracks

    async def _parse_single_audio_track(self, line: str, m3u8_url: str, fetch_segments: bool) -> HLSAudioTrack | None:
        """解析單一音訊軌道"""
        attrs = self._extract_attributes(
            line,
            {
                "name": self.PATTERNS["name"],
                "language": self.PATTERNS["language"],
                "uri": self.PATTERNS["uri"],
                "channels": self.PATTERNS["channels"],
                "bandwidth": self.PATTERNS["bandwidth"],
            },
        )

        if "uri" not in attrs:
            return None

        uri = urljoin(m3u8_url, attrs["uri"])
        name = attrs.get("name", "Unknown")
        language = attrs.get("language")
        bandwidth = int(attrs["bandwidth"]) if "bandwidth" in attrs else None
        channels = attrs.get("channels")

        tasks = []
        segments_task = None
        if fetch_segments:
            segments_task = asyncio.create_task(self._fetch_segments_safe(uri, "audio", f"'{name}' [{language}]"))
            tasks.append(segments_task)
        segments = (await asyncio.gather(*[t for t in tasks if t is not None]))[0]

        return HLSAudioTrack(
            name=name,
            language=language,
            uri=uri,
            bandwidth=bandwidth,
            channels=channels,
            segments=segments,
        )

    async def parse_media_playlist(self, playlist_url: str) -> HLSMediaPlaylist:
        """解析媒體播放清單"""
        resp = await self.get_request.get_request(playlist_url, use_proxy)
        lines = [line.strip() for line in re.findall(REGEX_HLS_PATTERN, resp) if line.strip()]

        segments = []
        is_encrypted = False
        encryption_key_uri = None
        current_duration = 0.0
        sequence = 0
        total_duration = 0.0

        for line in lines:
            if line.startswith("#EXT-X-KEY:") and "METHOD=AES-128" in line:
                is_encrypted = True
                attrs = self._extract_attributes(line, {"uri": self.PATTERNS["uri"]})
                if "uri" in attrs:
                    encryption_key_uri = urljoin(playlist_url, attrs["uri"])

            elif line.startswith("#EXTINF:"):
                attrs = self._extract_attributes(line, {"duration": self.PATTERNS["duration"]})
                current_duration = float(attrs.get("duration", 0.0))

            elif not line.startswith("#") and re.search(r"\.(ts|aac|mp4|m4a|m4v)\b", line):
                segment_url = urljoin(playlist_url, line)
                segments.append(HLSSegment(url=segment_url, duration=current_duration, sequence=sequence))
                total_duration += current_duration
                sequence += 1

        return HLSMediaPlaylist(
            segments=segments,
            is_encrypted=is_encrypted,
            encryption_key_uri=encryption_key_uri,
            encryption_key=None,
            total_duration=total_duration,
        )

    def extract_sorted_resolutions(self, lines: list[str]) -> list[tuple[int, int]]:
        """提取並排序所有分辨率"""
        resolutions = set()

        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF:"):
                attrs = self._extract_attributes(line, {"resolution": self.PATTERNS["resolution"]})
                if "resolution" in attrs:
                    w, h = attrs["resolution"]
                    resolutions.add((int(w), int(h)))

        return sorted(resolutions, key=lambda r: r[1])


HLS_Paser = HLSParser
