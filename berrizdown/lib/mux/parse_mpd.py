import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("parse_mpd", "periwinkle")


@dataclass
class Segment:
    t: int
    d: int
    r: int


@dataclass
class MediaTrack:
    id: str
    bandwidth: int
    codecs: str
    segments: list[Segment]
    init_url: str
    segment_urls: list[str]
    mime_type: str
    width: int | None = None
    height: int | None = None
    timescale: int | None = None
    audio_sampling_rate: int | None = None
    language: str | None = None
    segment_timeline: list[Segment] = field(default_factory=list)
    segment_template: str | None = None
    initialization_url: str | None = None


@dataclass
class SubtitleTrack:
    id: str
    language: str | None
    mime_type: str
    codecs: None
    bandwidth: int
    init_url: str | None
    segment_urls: list[str]
    segment_timeline: list[Segment]
    timescale: int | None = None
    segment_template: str | None = None


@dataclass
class MPDContent:
    video_tracks: list[MediaTrack]
    audio_tracks: list[MediaTrack]
    subtitle_tracks: list[SubtitleTrack]
    base_url: str
    drm_info: dict[str, Any]


class Codec:
    @staticmethod
    def match_codec(codec: str) -> str:
        if codec.startswith("avc1") or codec in ["avc", "avc1", "h264", "h.264"]:
            return "avc1"
        return codec


class MPDParser:
    """MPD 文件解析器"""

    NAMESPACES: dict[str, str] = {
        "": "urn:mpeg:dash:schema:mpd:2011",
        "cenc": "urn:mpeg:cenc:2013",
        "mspr": "urn:microsoft:playready",
    }

    DRM_SCHEMES: dict[str, Any] = {
        "default_KID": {
            "uri": "urn:mpeg:dash:mp4protection:2011",
            "attr": "{urn:mpeg:cenc:2013}default_KID",
            "validator": lambda v: len(v.strip().replace("-", "")) == 32,
            "transformer": lambda v: v.strip().replace("-", ""),
        },
        "playready_pssh": {
            "uri": "urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95",
            "xpath": "./mspr:pro",
            "validator": lambda v: bool(v),
        },
        "widevine_pssh": {
            "uri": "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed",
            "xpath": "./cenc:pssh",
            "validator": lambda v: len(v) < 300 and v.endswith("="),
        },
    }

    SUBTITLE_MIME_TYPES: set[str] = {
        "application/ttml+xml",
        "text/vtt",
        "text/m2pt",
        "application/mp4",
        "text/plain",
    }
    
    SUBTITLE_CODECS: set[str] = {"stpp", "wvtt", "ttml", "vtt"}

    def __init__(self, raw_mpd_text: Any, mpd_url: str):
        self.mpd_url: str = mpd_url
        self.root: ET.Element = self._parse_xml(raw_mpd_text)
        self.namespaces: dict[str, str] = self.NAMESPACES
        self.base_url: str = mpd_url.rsplit("/", 1)[0] + "/"

    def _parse_xml(self, text_response: str) -> ET.Element:
        """解析 XML 文字為 ElementTree Element"""
        xml_text: str = text_response
        if not isinstance(xml_text, str):
            raise TypeError(f"Expected text attribute to be str, got {type(xml_text)}")
        return ET.fromstring(xml_text)

    def _get_attr(
        self,
        element: ET.Element,
        attr: str,
        required: bool = False,
        attr_type: type = str,
        default: Any = None,
        elem_name: str = "Element",
    ) -> Any:
        """統一的屬性取得方法"""
        value: str = element.get(attr)

        if value is None:
            if required:
                raise ValueError(f"{elem_name} missing required attribute '{attr}'")
            return default

        if attr_type is int:
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"Invalid integer value '{value}' for attribute '{attr}'")

        return value

    def _parse_drm_info(self) -> dict[str, Any]:
        """從 MPD 解析 DRM/ContentProtection 訊息"""
        drm_info: dict[str, Any] = {}

        for key, config in self.DRM_SCHEMES.items():
            value: str | None = self._extract_drm_value(config)
            if value:
                drm_info[key] = value

        return drm_info

    def _extract_drm_value(self, config: dict[str, Any]) -> str | None:
        """提取單一 DRM 值"""
        prot: ET.Element = self.root.find(f".//ContentProtection[@schemeIdUri='{config['uri']}']", self.namespaces)

        if prot is None:
            return None

        # Get value
        if "attr" in config:
            value: str = prot.get(config["attr"], "")
        elif "xpath" in config:
            value: str = prot.findtext(config["xpath"], "", namespaces=self.namespaces)
        else:
            return None

        # 驗證和轉換
        if not value or not config.get("validator", lambda x: True)(value):
            return None

        transformer: Any = config.get("transformer", lambda x: x)
        return transformer(value)

    def _parse_segment_timeline(self, seg_template: ET.Element) -> list[Segment]:
        """解析 SegmentTimeline 為 Segment 列表"""
        seg_timeline: ET.Element = seg_template.find("./SegmentTimeline", self.namespaces)
        if seg_timeline is None:
            return []

        segments: list[Segment] = []
        # 追蹤累積時間
        current_time: int = 0  

        for s_elem in seg_timeline.findall("./S", self.namespaces):
            try:
                # 獲取屬性，t 可能是 None
                t_attr: int | None = self._get_attr(s_elem, "t", attr_type=int, default=None)
                d: int = self._get_attr(
                    s_elem, "d", attr_type=int, required=True, elem_name="Segment 'S'"
                )
                r: int = self._get_attr(s_elem, "r", attr_type=int, default=0)
                # 如果有 t 屬性，使用它 否則使用累積時間
                if t_attr is not None:
                    current_time = t_attr

                # 創建 Segment 對象
                segments.append(Segment(t=current_time, d=d, r=r))
                
                # 更新累積時間為下一個 segment 的開始位置
                current_time += d * (r + 1)

            except ValueError as e:
                logger.warning(f"Skipping invalid segment: {e}")

        return segments

    def _generate_segment_urls(
        self, rep_id: str, media_template: str, segments: list[Segment]
    ) -> list[str]:
        """生成所有片段的 URL 列表"""
        segment_urls: list[str] = []

        for seg in segments:
            urls = self._expand_segment(seg, rep_id, media_template)
            segment_urls.extend(urls)

        return segment_urls

    def _expand_segment(
        self, seg: Segment, rep_id: str, media_template: str
    ) -> list[str]:
        """展開單一 segment（處理重複）"""
        urls: list[str] = []
        current_time: int = seg.t

        for _ in range(seg.r + 1):
            url: str = self._format_segment_url(media_template, rep_id, current_time)
            urls.append(urljoin(self.base_url, url))
            current_time += seg.d

        return urls

    def _format_segment_url(self, template: str, rep_id: str, time: int) -> str:
        """格式化 segment URL"""
        return template.replace("$RepresentationID$", rep_id).replace(
            "$Time$", str(time)
        )

    def _extract_templates(self, seg_template: ET.Element) -> tuple[str, str]:
        """提取初始化和媒體模板"""
        init_template: str = seg_template.get("initialization")
        media_template: str = seg_template.get("media")

        if not init_template:
            raise ValueError("SegmentTemplate missing 'initialization' attribute")
        if not media_template:
            raise ValueError("SegmentTemplate missing 'media' attribute")

        return init_template, media_template

    def _extract_optional_attributes(
        self, rep: ET.Element, adapt_set: ET.Element, seg_template: ET.Element
    ) -> dict[str, Any]:
        mime_type: str = rep.get("mimeType") or adapt_set.get("mimeType", "")

        return {
            "width": self._get_attr(rep, "width", attr_type=int),
            "height": self._get_attr(rep, "height", attr_type=int),
            "audio_sampling_rate": self._get_attr(
                rep, "audioSamplingRate", attr_type=int
            ),
            "timescale": self._get_attr(
                seg_template, "timescale", attr_type=int, default=1
            ),
            "mime_type": mime_type,
        }

    def _is_subtitle_adapt_set(self, adapt_set: ET.Element, mime_type: str) -> bool:
        """判斷 AdaptationSet 是否為字幕軌道"""
        content_type = adapt_set.get("contentType", "")
        if content_type == "text":
            return True

        if mime_type in self.SUBTITLE_MIME_TYPES:
            return True

        for rep in adapt_set.findall("./Representation", self.namespaces):
            codecs: str = rep.get("codecs", "").lower()
            if any(codecs.startswith(c) for c in self.SUBTITLE_CODECS):
                return True

        return False

    def _parse_subtitle_representation(
        self,
        rep: ET.Element,
        adapt_set: ET.Element,
        lang: str | None,
    ) -> SubtitleTrack | None:
        """解析字幕 Representation 為 SubtitleTrack"""
        seg_template: ET.Element = rep.find("./SegmentTemplate", self.namespaces) or adapt_set.find(
            "./SegmentTemplate", self.namespaces
        )

        try:
            rep_id: str = self._get_attr(
                rep, "id", required=True, elem_name="Subtitle Representation"
            )
            bandwidth: int = self._get_attr(
                rep, "bandwidth", attr_type=int, default=0
            )
            codecs: str = rep.get("codecs") or adapt_set.get("codecs")
            mime_type: str = rep.get("mimeType") or adapt_set.get("mimeType", "")

            if seg_template is None:
                base_url_elem: ET.Element = rep.find(
                    "./BaseURL", self.namespaces
                ) or adapt_set.find("./BaseURL", self.namespaces)
                segment_url: str | None = (
                    urljoin(self.base_url, base_url_elem.text.strip())
                    if base_url_elem is not None and base_url_elem.text
                    else None
                )

                return SubtitleTrack(
                    id=rep_id,
                    language=lang or None,
                    mime_type=mime_type,
                    codecs=codecs,
                    bandwidth=bandwidth,
                    init_url=None,
                    segment_urls=[segment_url] if segment_url else [],
                    segment_timeline=[],
                    timescale=None,
                    segment_template=None,
                )

            segments: list[Segment] = self._parse_segment_timeline(seg_template)
            init_template, media_template = self._extract_templates(seg_template)
            init_url: str = urljoin(
                self.base_url, init_template.replace("$RepresentationID$", rep_id)
            )
            segment_urls: list[str] = self._generate_segment_urls(rep_id, media_template, segments)
            timescale: int = self._get_attr(
                seg_template, "timescale", attr_type=int, default=1
            )

            return SubtitleTrack(
                id=rep_id,
                language=lang or None,
                mime_type=mime_type,
                codecs=codecs,
                bandwidth=bandwidth,
                init_url=init_url,
                segment_urls=segment_urls,
                segment_timeline=segments,
                timescale=timescale,
                segment_template=media_template,
            )

        except (ValueError, TypeError) as e:
            rep_id: str = rep.get("id", "unknown")
            logger.warning(f"Failed to parse Subtitle Representation {rep_id}: {e}")
            return None

    def _parse_representation(
        self,
        rep: ET.Element,
        adapt_set: ET.Element,
        lang: str | None = None,
    ) -> MediaTrack | None:
        """解析單一 Representation 為 MediaTrack"""
        # 查找 SegmentTemplate
        seg_template: ET.Element = rep.find("./SegmentTemplate", self.namespaces) or adapt_set.find(
            "./SegmentTemplate", self.namespaces
        )

        if seg_template is None:
            return None

        try:
            # 提取基本資訊
            rep_id: str = self._get_attr(
                rep, "id", required=True, elem_name="Representation"
            )
            bandwidth: int = self._get_attr(
                rep,
                "bandwidth",
                required=True,
                attr_type=int,
                elem_name=f"Representation {rep_id}",
            )
            raw_codecs: str = self._get_attr(
                rep, "codecs", required=True, elem_name=f"Representation {rep_id}"
            )
            codecs: str = Codec.match_codec(raw_codecs)

            # 解析 segments
            segments: list[Segment] = self._parse_segment_timeline(seg_template)

            # 取得模板
            init_template, media_template = self._extract_templates(seg_template)

            # 生成 URLs
            init_url: str = urljoin(self.base_url, init_template.replace("$RepresentationID$", rep_id))
            segment_urls: list[str] = self._generate_segment_urls(rep_id, media_template, segments)

            # 提取可選屬性
            optional_attrs: dict[str, any] = self._extract_optional_attributes(rep, adapt_set, seg_template)

            return MediaTrack(
                id=rep_id,
                bandwidth=bandwidth,
                codecs=codecs,
                segments=segments,
                init_url=init_url,
                segment_urls=segment_urls,
                segment_timeline=segments,
                segment_template=media_template,
                initialization_url=init_url,
                language=lang or None,
                **optional_attrs,
            )

        except (ValueError, TypeError) as e:
            rep_id: str = rep.get("id", "unknown")
            logger.warning(f"Failed to parse Representation {rep_id}: {e}")
            return None

    async def parse_all_tracks(self) -> MPDContent:
        """解析 MPD 並返回所有視訊 音訊 字幕軌道"""
        period: ET.Element = self.root.find("./Period", self.namespaces)
        if period is None:
            raise ValueError("MPD contains no Period elements")

        video_tracks: list[MediaTrack] = []
        audio_tracks: list[MediaTrack] = []
        subtitle_tracks: list[SubtitleTrack] = []

        for adapt_set in period.findall("./AdaptationSet", self.namespaces):
            # 從 AdaptationSet 層級讀取 (可能是空的)
            adapt_mime_type: str = adapt_set.get("mimeType", "")
            lang: str | None = adapt_set.get("lang") or None

            if self._is_subtitle_adapt_set(adapt_set, adapt_mime_type):
                for rep_element in adapt_set.findall(
                    "./Representation", self.namespaces
                ):
                    track = self._parse_subtitle_representation(
                        rep_element, adapt_set, lang
                    )
                    if track:
                        subtitle_tracks.append(track)
                continue

            for rep_element in adapt_set.findall("./Representation", self.namespaces):
                track = self._parse_representation(rep_element, adapt_set, lang)

                if track:
                    # 先使用 AdaptationSet 的 mimeType
                    # 不存在用 Representation 的 mimeType (已存儲在 track.mime_type)
                    effective_mime: str = adapt_mime_type or track.mime_type

                    if effective_mime.startswith("video"):
                        video_tracks.append(track)
                    elif effective_mime.startswith("audio"):
                        audio_tracks.append(track)

        return MPDContent(
            video_tracks=video_tracks,
            audio_tracks=audio_tracks,
            subtitle_tracks=subtitle_tracks,
            base_url=self.base_url,
            drm_info=self._parse_drm_info(),
        )

    def validate_mpd_structure(self) -> list[str]:
        issues: list[str] = []

        period: ET.Element | None = self.root.find("./Period", self.namespaces)
        if period is None:
            issues.append("ERROR: No Period element found")
            return issues

        adapt_sets: list[ET.Element] = period.findall("./AdaptationSet", self.namespaces)
        if not adapt_sets:
            issues.append("WARNING: No AdaptationSet elements found")

        return issues
