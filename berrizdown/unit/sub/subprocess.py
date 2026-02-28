import pysubs2

from berrizdown.static.color import Color
from berrizdown.lib.path import Path
from berrizdown.unit.sub.webvtt import merge_segmented_webvtt
from berrizdown.lib.mux.parse_hls import HLSSubTrack
from berrizdown.lib.mux.parse_mpd import SubtitleTrack
from berrizdown.unit.handle.handle_log import setup_logging

from rich.progress import track


logger = setup_logging("subprocess", "periwinkle")


class SubtitleProcessor:
    def __init__(
        self, track: HLSSubTrack | SubtitleTrack,
        segments: list[Path],
        ) -> None:
        self.track: HLSSubTrack | SubtitleTrack = track
        self.segments: list[Path] = segments

    def check_sub_type(self) -> str:
        match self.track.mime_type:
            case "text/mp2t":
                return "webvtt"
            case "application/mp4":
                return "ttml"
            
    def webvtt_merge(self) -> str:
        return self.merge_vtt_from_path_list()
    
    def webvtt2srt(self, vtt_content: str) -> str:
        return self.webvtt2srt(vtt_content)

    def merge_vtt_from_path_list(self) -> str:
        raw_parts: list[str] = []
        
        for p in track(self.segments, description=f"　[cyan]{self.track.language} [blue]subtitle[/blue]"):
            if p.exists():
                content = p.read_text(encoding="utf-8").strip()
                if content:
                    raw_parts.append(content)
            else:
                logger.error(f"{Color.fg('red')}Warning: Segment file {p} does not exist.{Color.reset()}")
                raise FileNotFoundError(f"Segment file {p} does not exist.")
                
        full_vtt_raw: str = "\n\n".join(raw_parts)
        merged_vtt_string: str = merge_segmented_webvtt(full_vtt_raw)

        return merged_vtt_string
    
    def webvtt2srt(self, vtt_content: str) -> str:
        # pysubs2 會自動處理 VTT 的 Header 和時間戳格式
        subs: pysubs2.SSAFile = pysubs2.SSAFile.from_string(vtt_content)
        srt_content: str = subs.to_string("srt")
        return srt_content
    
    def process_subtitle(self) -> str:
        """input subtitle track and segments, output processed subtitle content"""
        sub_type: str = self.check_sub_type()
        if sub_type == "webvtt":
            merged_vtt: str = self.webvtt_merge()
            return self.webvtt2srt(merged_vtt)
        else:
            raise ValueError(f"Unsupported subtitle type: {sub_type}")