import os

import ffmpeg
from berrizdown.static.parameter import paramstore


class VideoInfo:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        self.path = path
        
        if paramstore.get("ffprobe_path_ok") is True:
            self._probe_data = ffmpeg.probe(self.path)

            self._format = self._probe_data["format"]
            self._vstreams = self._probe_data["streams"]

            self._size_bytes = int(self._format.get("size", 0))
            self._duration_sec = float(self._format.get("duration", 0.0))

    @property
    def size(self) -> str:
        size_gb = self._size_bytes / (1024**3)
        size_mb = self._size_bytes / (1024**2)
        if size_gb >= 1:
            return f"{size_gb:.2f} GB"
        else:
            return f"{int(size_mb)} MB"

    @property
    def duration(self) -> str:
        total_seconds = int(self._duration_sec)
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    @property
    def codec(self) -> str:
        H265_NAMES = ["hevc", "h.265", "x265", "h265"]
        AV1_NAMES = ["av1", "av01"]
        VP9_NAMES = ["vp9"]
        H264_NAMES = ["avc", "avc1", "h.264", "x264", "h264"]

        for stream in self._vstreams:
            if stream.get("codec_type") == "video":
                codec_name = stream.get("codec_name", "unknown").lower()
                if any(name in codec_name for name in H265_NAMES):
                    return "H265"
                if any(name in codec_name for name in AV1_NAMES):
                    return "AV1"
                if any(name in codec_name for name in VP9_NAMES):
                    return "VP9"
                if any(name in codec_name for name in H264_NAMES):
                    return "H264"
                return codec_name.upper()
        return "unknown"

    @property
    def quality_label(self) -> str:
        resolution_map = {
            144: "144p",
            256: "144p",
            240: "240p",
            426: "240p",
            360: "360p",
            640: "360p",
            480: "480p",
            854: "480p",
            540: "540p",
            960: "540p",
            720: "720p",
            1280: "720p",
            1080: "1080p",
            1920: "1080p",
            1440: "1440p",
            2560: "1440p",
            2160: "2160p",
            3840: "2160p",
            2880: "2880p",
        }
        for stream in self._vstreams:
            if stream["codec_type"] == "video":
                height = int(stream.get("height", 0))
                return resolution_map.get(height, f"{height}p")
        return "unknown"

    @property
    def audio_codec(self) -> str:
        audio_stream = next(
            (stream for stream in self._vstreams if stream.get("codec_type") == "audio"),
            None,
        )
        if audio_stream:
            if audio_stream.get("channels", "") == 2:
                suffix: str = "2.0"
            elif audio_stream.get("channels", "") == 6:
                suffix = "5.1"
            return f"{audio_stream.get('codec_name', 'unknown').upper()}{suffix}"
        return "unknown"

    def as_dict(self) -> dict:
        if paramstore.get("ffprobe_path_ok") is True:
            return {
                "size": self.size,
                "duration": self.duration,
                "video_codec": self.codec,
                "quality": self.quality_label,
                "audio_codec": self.audio_codec,
            }
        else:
            return {
                "size": 0,
                "duration": -1,
                "video_codec": "unknown",
                "quality": "unknown",
                "audio_codec": "unknown",
            }