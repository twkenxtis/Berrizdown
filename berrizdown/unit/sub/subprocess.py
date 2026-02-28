import io
import struct
import xml.etree.ElementTree as ET
from collections.abc import Iterable

import pysubs2

from berrizdown.static.color import Color
from berrizdown.lib.path import Path
from berrizdown.unit.sub.webvtt import merge_segmented_webvtt
from berrizdown.lib.mux.parse_hls import HLSSubTrack
from berrizdown.lib.mux.parse_mpd import SubtitleTrack
from berrizdown.unit.handle.handle_log import setup_logging

from rich.progress import TaskID, track, Progress


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

    @staticmethod
    def ttml_time_to_seconds(time_str: str) -> float:
        """將 TTML 時間格式 (HH:MM:SS.mmm) 轉為秒數"""
        h, m, s = time_str.split(":")
        return float(h) * 3600 + float(m) * 60 + float(s)

    @staticmethod
    def seconds_to_srt_time(seconds: float) -> str:
        """將秒數轉為 SRT 時間格式 (HH:MM:SS,mmm)"""
        total_ms: float = round(seconds * 1000)
        millis = total_ms % 1000
        total_s = total_ms // 1000
        secs = total_s % 60
        mins = (total_s // 60) % 60
        hours = total_s // 3600
        return f"{hours:02}:{mins:02}:{secs:02},{millis:03}"

    def process_subtitle(self, init_path: list[Path] | None) -> str:
        """input subtitle track and segments, output processed subtitle content"""
        sub_type: str = self.check_sub_type()
        
        if isinstance(init_path, list):
            if len(init_path) >= 1 :
                init_path: Path = init_path[0]

        if sub_type == "webvtt":
            merged_vtt: str = self.merge_vtt_from_path_list()
            return self.webvtt2srt(merged_vtt)
        elif sub_type == "ttml":
            merge_srt: str = STPPSubtitleExtractor(self.track, self.segments, init_path).to_srt_string()
            return merge_srt
        else:
            raise ValueError(f"Unsupported subtitle type: {sub_type}")


class STPPSubtitleExtractor:
    """
    將 STPP 格式的 init + segments 轉換為 TTML 或 SRT 字串
    """
    def __init__(self, track: HLSSubTrack | SubtitleTrack, segments: list[Path], init_path: Path) -> None:
        self.track: HLSSubTrack | SubtitleTrack = track
        self.segments: list[Path] = segments
        self.init_path: Path = init_path

    def _merge_to_buffer(self) -> io.BytesIO:
        if not self.segments:
            raise FileNotFoundError(f"No segment files found：{self.segments}")
        if not self.init_path.exists():
            raise FileNotFoundError(f"Init file {self.init_path} does not exist.")
        
        buffer: io.BytesIO = io.BytesIO()

        with Progress() as progress:
            task: TaskID = progress.add_task(
                description=f"　[cyan]{self.track.language} [blue]subtitle[/blue]",
                total=len(self.segments) + 1
            )

            # 先寫入 init.mp4
            with self.init_path.open("rb") as f:
                buffer.write(f.read())
            progress.update(task, advance=1)

            # 依序寫入所有剩餘切片
            for seg in self.segments:
                with seg.open("rb") as f:
                    buffer.write(f.read())
                progress.update(task, advance=1)

        buffer.seek(0)
        return buffer

    def _extract_ttml_fragments(self, buffer: io.BytesIO) -> list[str]:
        """
        從 MP4 緩衝區中提取 TTML (XML) 字幕碎片
        核心邏輯是遍歷 MP4 的 box 結構，找到 mdat box 並讀取其內容
        """
        buffer.seek(0)
        data: bytes = buffer.read()
        fragments: list[str] = []

        pos: int = 0
        # 遍歷資料直到不足以構成一個基本的 box header (4 byte size + 4 byte type)
        while pos + 8 <= len(data):
            # 讀取 box 的 size (前 4 bytes)
            size_bytes: bytes = data[pos : pos + 4]
            if len(size_bytes) < 4:
                break

            # 將 4 bytes 的 size 轉為整數 (大端序)
            size: int = struct.unpack(">I", size_bytes)[0]

            if size == 0:
                break
            if size < 8:
                pos += 4
                continue

            box_type: bytes = data[pos + 4 : pos + 8]

            if box_type == b"mdat":
                # payload_start 跳過 header (8 bytes)
                payload_start: int = pos + 8
                # payload_end 為當前位置加上 box 的總大小
                payload_end: int = pos + size

                if payload_end > len(data):
                    # 邊界檢查：如果 mdat 資料被截斷，則記錄警告並停止
                    logger.warning("Warning: The last mdat character was truncated and ignored")
                    break

                content: bytes = data[payload_start:payload_end]

                xml_data: bytes = content
                # 如果前 4 bytes 不是 ASCII 字元，通常表示它是長度前綴
                if len(content) >= 4 and not content[:4].isascii():
                    try:
                        # 讀取內部的實際長度
                        sample_len: int = struct.unpack(">I", content[:4])[0]
                        # 驗證長度是否合理
                        if 4 + sample_len <= len(content):
                            # 移除長度前綴 只取真正的 XML 資料
                            xml_data = content[4 : 4 + sample_len]
                    except Exception:
                        pass

                try:
                    # 將 bytes 轉為 UTF-8 字串
                    text: str = xml_data.decode("utf-8", errors="strict").strip()
                    # 驗證是否為 XML 碎片
                    if text.startswith("<"):
                        fragments.append(text)
                except UnicodeDecodeError:
                    logger.warning(f"Warning: mdat cannot be decoded in UTF-8 @ offset {pos}")

            # 支援 Large Size Box (如果 size == 1，表示實際 size 在隨後的 8 bytes 中)
            if size == 1 and pos + 16 <= len(data):
                size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
                pos += 8

            # 跳過當前 box，移動到下一個 box
            pos += size

        return fragments

    def _build_ttml_tree(
        self,
        fragments: Iterable[str],
    ) -> ET.ElementTree:
        lang: str = self.track.language if self.track.language else "und"

        root: ET.Element = ET.Element(
            "tt",
            {
                "xmlns": "http://www.w3.org/ns/ttml",
                "xml:lang": lang,
            },
        )

        body: ET.Element = ET.SubElement(root, "body")
        div: ET.Element = ET.SubElement(body, "div")

        for idx, frag in enumerate(fragments, 1):
            try:
                frag_root: ET.Element = ET.fromstring(frag)
                for p in frag_root.iterfind(".//{http://www.w3.org/ns/ttml}p"):
                    div.append(p)
            except ET.ParseError as e:
                logger.warning(f"Failed to parse the {idx}th fragment, skipping the beginning: {frag[:60]!r}\n Error: {e}")

        return ET.ElementTree(root)

    @staticmethod
    def _ttml_tree_to_string(tree: ET.ElementTree) -> str:
        buffer: io.BytesIO = io.StringIO()
        tree.write(buffer, encoding="unicode", xml_declaration=True)
        return buffer.getvalue()

    @staticmethod
    def _ttml_tree_to_srt_string(tree: ET.ElementTree) -> str:
        root: ET.Element = tree.getroot()
        ns: dict[str, str] = {"tt": "http://www.w3.org/ns/ttml"}

        cues: list[str] = []

        for i, p in enumerate(root.findall(".//tt:p", ns), 1):
            begin: str = p.get("begin", "")
            end: str = p.get("end", "")
            if not begin or not end:
                continue

            text_parts: list[str] = []
            for elem in p.iter():
                if elem.text:
                    text_parts.append(elem.text.strip())
                if elem.tail:
                    text_parts.append(elem.tail.strip())

            text: str = "\n".join(line for line in text_parts if line).strip()
            if not text:
                continue

            def fmt_time(t: str) -> str:
                if t.count(":") == 1:
                    t = "00:" + t
                if "." not in t:
                    t += ".000"
                # 簡單清理多餘小數點或格式錯誤
                t = t.replace(".", " ").split()[0] + "." + t.split(".")[-1]
                h, m, rest = t.split(":", 2)
                s, ms = rest.split(".")
                ms = (ms + "000")[:3]
                return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms}"

            try:
                begin_fmt: str = fmt_time(begin)
                end_fmt: str = fmt_time(end)
                cues.append(f"{i}\n{begin_fmt} --> {end_fmt}\n{text}\n")
            except Exception as e:
                logger.warning(f"cue {i} time format error, skipped: {begin} → {end} ({e})")

        return "\n".join(cues).rstrip() + "\n"

    def to_ttml_string(self) -> str:
        buffer: io.BytesIO = self._merge_to_buffer()
        fragments: list[str] = self._extract_ttml_fragments(buffer)

        if not fragments:
            raise ValueError("No valid TTML fragment found")

        tree: ET.ElementTree = self._build_ttml_tree(fragments)

        return self._ttml_tree_to_string(tree)

    def to_srt_string(self) -> str:
        buffer: io.BytesIO = self._merge_to_buffer()
        fragments: list[str] = self._extract_ttml_fragments(buffer)

        if not fragments:
            raise ValueError("No valid TTML fragment found")

        tree: ET.ElementTree = self._build_ttml_tree(fragments)
        return self._ttml_tree_to_srt_string(tree)