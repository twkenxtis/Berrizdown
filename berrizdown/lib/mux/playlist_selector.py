import sys
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Optional, Union

from InquirerPy import inquirer
from rich.console import Console

from berrizdown.lib.mux.parse_hls import HLSAudioTrack, HLSContent, HLSSegment, HLSVariant, HLSSubTrack
from berrizdown.lib.mux.parse_mpd import MediaTrack, MPDContent, Segment, SubtitleTrack
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("playlist_selector", "periwinkle")


class TrackType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUB = "subtitle"


class SourceType(Enum):
    HLS = "hls"
    MPD = "mpd"


@dataclass
class SegmentInfo:
    url: str
    start_time: float
    duration: float
    index: int


@dataclass
class SelectedContent:
    video_track: HLSVariant | MediaTrack | None
    audio_track: HLSAudioTrack | MediaTrack | None
    sub_track: list[HLSSubTrack | SubtitleTrack] | HLSSubTrack | SubtitleTrack | None
    content_type: str
    base_url: str
    start_time: float | None = None
    end_time: float | None = None


class PlaylistSelector:
    TIME_TOLERANCE = 0.05  # 50ms

    def __init__(
        self,
        hls_content: HLSContent | None = None,
        mpd_content: MPDContent | None = None,
        select_mode: str = "all",
        start_time: float | None = None,
        end_time: float | None = None,
    ):
        self.hls_content: HLSContent | None = hls_content
        self.mpd_content: MPDContent | None = mpd_content
        self.select_mode: str = select_mode.lower()
        self.start_time: float | None = self._validate_time(start_time, "start_time")
        self.end_time: float | None = self._validate_time(end_time, "end_time")
        self._validate_initialization()

    def _validate_initialization(self):
        """驗證初始化參數"""
        if not self.hls_content and not self.mpd_content:
            raise ValueError("At least HLS or MPD content is required")

        if self.select_mode not in {"hls", "mpd", "all"}:
            logger.warning(f"Invalid select_mode '{self.select_mode}', defaulting to 'all'")
            self.select_mode = "all"

        if self._is_time_range_invalid():
            logger.warning("Invalid time range (start >= end), ignoring time filter")
            self.start_time = self.end_time = None

        # 記錄時間過濾狀態
        if self.start_time is not None or self.end_time is not None:
            start_str: str = f"{self.start_time:.2f}s" if self.start_time is not None else "START"
            end_str: str = f"{self.end_time:.2f}s" if self.end_time is not None else "END"
            logger.info(
                f"{Color.fg('cyan')}Time range filter enabled: {start_str} → {end_str}. Minor segment count differences between tracks are expected due to codec alignment.{Color.reset()}"
            )

    def _validate_time(self, time_val: float | None, name: str) -> float | None:
        """驗證時間參數"""
        if time_val is not None and time_val < 0:
            logger.warning(f"Invalid {name} ({time_val}), setting to 0")
            return 0.0
        return time_val

    def _is_time_range_invalid(self) -> bool:
        """檢查時間範圍是否無效"""
        return self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time

    async def select_tracks(
        self,
        v_resolution_choice: str,
        a_resolution_choice: str,
        video_codec: str | None = None,
        s_lang_choice: str | list[str] | None = "all",
    ) -> SelectedContent:
        """"選擇視訊和音訊軌道"""
        selected_video, video_type = await self._select_single_track(v_resolution_choice, TrackType.VIDEO, video_codec)
        selected_audio, audio_type = await self._select_single_track(a_resolution_choice, TrackType.AUDIO)
        if isinstance(s_lang_choice, str):
            s_lang_choice: list[str] = [s_lang_choice]
        elif isinstance(s_lang_choice, list) and len(s_lang_choice) == 0:
            s_lang_choice: str = "all"
        if isinstance(s_lang_choice, tuple):
            s_lang_choice: list[str] = list(s_lang_choice)
        selected_sub, sub_type = await self._select_subtitle_tracks(s_lang_choice)

        # 更新 paramstore
        self._update_paramstore(video_type, audio_type)
        content_type: str | None = video_type if video_type == audio_type else "mixed"
        base_url: str | None = self._get_base_url(video_type, audio_type)

        # 應用時間過濾
        actual_start, actual_end = None, None
        if self.start_time is not None or self.end_time is not None:
            paramstore._store["subtitle_offset_start"] = True
            logger.info(f"Applying time filter: {self.start_time} → {self.end_time}")

            # 分別過濾並獲取實際時間範圍
            selected_video, v_start, v_end = await self._apply_filters(selected_video, video_type)
            selected_audio, a_start, a_end = await self._apply_filters(selected_audio, audio_type)

            if isinstance(selected_sub, list):
                filtered_sub: list[HLSSubTrack | SubtitleTrack] = []
                for sub, stype in zip(selected_sub, sub_type):
                    filtered, _, _ = await self._apply_filters(sub, stype)
                    filtered_sub.append(filtered)
                selected_sub = filtered_sub
            else:
                selected_sub, _, _ = await self._apply_filters(selected_sub, sub_type)

            # 使用影像時間作為基準對GOP
            actual_start: float | None = v_start if v_start is not None else a_start
            actual_end: float | None = v_end if v_end is not None else a_end

            self._log_filter_results(selected_video, selected_audio, actual_start, actual_end)
        else:
            logger.info("No time filtering applied")

        return SelectedContent(
            video_track=selected_video,
            audio_track=selected_audio,
            sub_track=selected_sub,
            content_type=content_type or "unknown",
            base_url=base_url,
            start_time=actual_start,
            end_time=actual_end,
        )

    async def _select_single_track(
        self,
        choice: str,
        track_type: TrackType,
        codec: str | None = None,
    ) -> tuple[HLSVariant | HLSAudioTrack | HLSSubTrack | MediaTrack | SubtitleTrack | None, str | None]:
        """統一軌道選擇"""

        if choice.lower() == "none":
            return None, None
        if choice.lower() in {"ask", "as"}:
            return await self._ask_track(track_type)
        return await self._auto_select_track(int(choice), track_type)

    async def _ask_track(
        self, track_type: TrackType
    ) -> tuple[
        Optional[Union["MediaTrack", list["MediaTrack"]]],
        Optional[Union[str, list[str]]],
    ]:
        """交互式選擇軌道 單選回傳 (track, label) track_type 是 SUB 改為複選並回傳 ( [tracks], [labels] )"""
        raw_items: list[tuple] = self._collect_all_track_items(track_type)

        if not raw_items:
            logger.warning("No %s tracks available", track_type.value)
            return None, None

        # 收集並標準化項目
        items: list[dict] = []
        for it in raw_items:
            # 2025.12.29 Berriz AI subtitle track HLS+MPD so is 6
            if not isinstance(it, (list, tuple)) or len(it) < 6:
                continue

            def norm_key(v: Any) -> float:
                if v is None:
                    return float("inf")
                try:
                    return float(v)
                except Exception:
                    return float("inf")

            items.append({
                "sort_key": (norm_key(it[0]), norm_key(it[1]), norm_key(it[2])),
                "label": str(it[3]),
                "value": it[4],
                "payload": it[5],
            })

        if not items:
            logger.warning("No valid %s track items after filtering", track_type.value)
            return None, None

        # 排序
        items.sort(key=lambda d: d["sort_key"])

        # 構造 choices 顯示字串（包含索引）與對應 map
        choices: list[str] = [f"{idx+1}. {it['label']}" for idx, it in enumerate(items)]
        value_map: dict[str, tuple] = {choices[idx]: (items[idx]["value"], items[idx]["label"]) for idx in range(len(items))}
        
        try:
            # 如果是字幕使用複選
            if track_type is TrackType.SUB:
                selected: inquirer = await inquirer.checkbox(
                    message=f"Choose one or more {track_type.value} tracks [{self.select_mode.upper()}]:",
                    choices=choices,
                    default=[choices[-1]],
                ).execute_async()
                
                if not selected:
                    logger.info("No subtitle tracks selected or user cancelled")
                    return None, None

                selected_values: list["MediaTrack"] = []
                selected_labels: list[str] = []
                for sel in selected:
                    val_label: tuple | None = value_map.get(sel)
                    if val_label:
                        val, lbl = val_label
                        selected_values.append(val)
                        selected_labels.append(lbl)

                if not selected_values:
                    return None, None

                return selected_values, selected_labels

            # 否則維持單選行為
            answer: inquirer = await inquirer.select(
                message=f"Choose {track_type.value} track [{self.select_mode.upper()}]:",
                choices=choices,
                default=choices[-1],
            ).execute_async()

        except KeyboardInterrupt:
            logger.info("User cancelled track selection")
            return None, None
        except Exception as e:
            logger.exception("Failed to prompt for track selection: %s", e)
            return None, None

        # 單選回傳
        return value_map.get(answer, (None, None))

    async def _auto_select_track(
        self, target: int, track_type: TrackType
    ) -> tuple[HLSVariant | HLSAudioTrack | HLSSubTrack | MediaTrack | SubtitleTrack | None, str | None]:
        """自動選擇軌道"""
        candidates: list[tuple, str, Any] = self._collect_all_candidates(target, track_type)
        if not candidates:
            if track_type == TrackType.AUDIO:
                return await self._fallback_audio_selection(target)
            raise ValueError(f"{track_type.value} track not found for target {target}")

        best: tuple = max(candidates, key=lambda x: x[2])
        #logger.info(f"Auto-select {Color.fg('sea_green')}{track_type.value}: {Color.reset()}{Color.fg('light_gray')}[{best[1].upper()}] @ {best[2] // 1000:,} kbps{Color.reset()}")
        return best[0], best[1]

    def _gather_all(self) -> tuple[list[Any], list[str]]:
        subs: list[Any] = []
        types: list[str] = []
        seen_languages: set[str | None] = set()
        
        for source in [SourceType.HLS, SourceType.MPD]:
            if self.select_mode in {source.value, "all"}:
                for t in self._get_tracks(source, TrackType.SUB):
                    lang: str = t.__dict__.get("language")
                    
                    if lang not in seen_languages:
                        logger.debug(f"Adding language: {lang}")
                        subs.append(t)
                        types.append(source.value)
                        seen_languages.add(lang)
                    else:
                        logger.debug(f"Skipping duplicate language: {lang}")
        return subs, types

    async def _select_subtitle_tracks(
        self,
        choice: str | list[str] | None,
        ) -> tuple[list[Any] | None, list[str] | None]:
        try:
            c: str | list[str] | None = choice.lower()
        except AttributeError:
            c: str | list[str] | None = choice

        if c == "none":
            return None, None
        
        subs, types = self._gather_all()
        # types只會同時有一種hls or mpd
        
        if isinstance(c, str) and c in {"ask", "as"} or choice == ["ask"]:
            print(f"{Color.fg("light_gray")}Space: select/deselect; ↑↓: move{Color.reset()}")
            track, src = await self._ask_track(TrackType.SUB)
            return track, src

        if isinstance(c, str) and c == "all" or choice == ["all"]:
            print("run heere")
            if not subs:
                logger.warning("No subtitle tracks found")
                return None, None
            
            logger.info(
                f"{Color.fg('sea_green')}subtitle: {Color.reset()}"
                f"{Color.fg('light_gray')}all ({len(subs)} tracks){Color.reset()}"
            )
            return subs, types

        if isinstance(choice, list) and choice not in {"all", "ask"}:
            LANG_MAP: dict[str, str] = {
                "zh-tw": "zh-Hans",
                "zh-cn": "zh-Hans",
                "zh-hant": "zh-Hans",
                "zh-hans": "zh-Hans",
                "zho": "zh-Hans",
                "eng": "en",
                "kor": "ko",
                "japan": "ja",
                "jpn": "ja"
            }
            VALID_LANGS = {"ko", "ja", "zh-Hans", "en"}
            c: list[str] = [
                n
                for x in choice
                for s in x.split(',')
                if (n := LANG_MAP.get(s.strip().lower(), s.strip().lower())) in VALID_LANGS
            ]
            # 就地更新 subs 只保留 language 在 s_lang_choice 裡的物件
            subs[:] = [sub for sub in subs if sub.__dict__.get("language") in c]
            return subs, types
    
    def _collect_all_track_items(self, track_type: TrackType) -> list[tuple]:
        """收集所有軌道項目 並在字幕類型下防止重複取得"""
        items: list[tuple] = []
        
        subtitle_already_found: bool = False

        if self.select_mode in {"hls", "all"} and self.hls_content:
            if track_type == TrackType.SUB and subtitle_already_found:
                pass
            else:
                source_items: list[tuple] = self._collect_source_items(SourceType.HLS, track_type)
                items.extend(source_items)
                if track_type == TrackType.SUB and source_items:
                    subtitle_already_found = True
                    
        if self.select_mode in {"mpd", "all"} and self.mpd_content:
            if track_type == TrackType.SUB and subtitle_already_found:
                pass
            else:
                source_items: list[tuple] = self._collect_source_items(SourceType.MPD, track_type)
                items.extend(source_items)
                if track_type == TrackType.SUB and source_items:
                    subtitle_already_found = True

        return items

    def _collect_source_items(self, source: SourceType, track_type: TrackType) -> list[tuple]:
        """從特定來源收集軌道項目"""
        tracks: list = self._get_tracks(source, track_type)
        if not tracks:
            return []
        items: list[tuple] | None = [self._format_track_item(track, source, track_type) for track in tracks]
        # 過濾 None
        return [item for item in items if item is not None]

    def _get_tracks(self, source: SourceType, track_type: TrackType) -> list:
            """取得指定來源和類型的軌道列表"""
            content: HLSContent | MPDContent | None = self.hls_content if source == SourceType.HLS else self.mpd_content
            if not content:
                return []

            if track_type == TrackType.VIDEO:
                return content.video_variants if source == SourceType.HLS else content.video_tracks
            elif track_type == TrackType.AUDIO:
                return content.audio_tracks
            else:
                if source == SourceType.HLS:
                    # HLS is "sub_tracks"
                    return getattr(content, "sub_tracks", [])
                else:
                    # MPD is "subtitle_tracks"
                    return getattr(content, "subtitle_tracks", [])

    def _format_track_item(self, track: Any, source: SourceType, track_type: TrackType) -> tuple | None:
        """格式化單一軌道項目"""
        if track_type == TrackType.VIDEO:
            return self._format_video_item(track, source)
        elif track_type == TrackType.AUDIO:
            return self._format_audio_item(track, source)
        elif track_type == TrackType.SUB:
            return self._format_subtitle_item(track, source)
        else:
            logger.error(f"Invalid track type: {track_type}")
            return None

    def _format_video_item(self, track: Any, source: SourceType) -> tuple | None:
        """音訊軌轉換"""
        if source == SourceType.HLS:
            if not hasattr(track, "resolution") or not track.resolution:
                return None
            w, h = track.resolution
            bw_kbps = track.bandwidth // 1000
            codec: str = track.codecs or "N/A"
            text: str = f"[HLS] {w}x{h} | {bw_kbps:,} kbps | {codec}"
            return (h, w, track.bandwidth, text, track, "hls")
        elif source == SourceType.MPD:
            if not track.width or not track.height:
                return None
            bw_kbps = track.bandwidth // 1000
            text: str = f"[MPD] {track.width}x{track.height} | {bw_kbps:,} kbps | {track.codecs}"
            return (track.height, track.width, track.bandwidth, text, track, "mpd")
        return None

    def _format_audio_item(self, track: Any, source: SourceType) -> tuple | None:
        """音訊軌轉換"""
        lang: str | None = getattr(track, "language", "N/A")
        bw: str | None = getattr(track, "bandwidth", 0)

        if source == SourceType.HLS:
            name: str = getattr(track, "name", "Unknown")
            bw_str: str = f"{bw // 1000}kbps" if bw else "≒189kbps"
            text: str = f"[HLS] [{lang}] {name} | {bw_str}"
            return (bw, 0, 0, text, track, "hls")
        else: # MPD
            if not hasattr(track, "id"):
                return None
            bw_kbps: int = bw // 1000
            rate: str | None = getattr(track, "audio_sampling_rate", None)
            rate_str: str = f"{rate}Hz" if rate else "N/A"
            text: str = f"[MPD] [{lang}] {track.id} | {bw_kbps}kbps / {rate_str}"
            return (bw, 0, 0, text, track, "mpd")

    def _format_subtitle_item(self, track: Any, source: SourceType) -> tuple | None:
        """字幕軌道格式化"""
        lang: str | None = getattr(track, "language", None) or "N/A"
        bw: int = getattr(track, "bandwidth", 0)
        mime: str = getattr(track, "mime_type", "")
        codecs: str = getattr(track, "codecs", None) or "N/A"

        if source == SourceType.HLS:
            # HLSSubTrack
            name: str = getattr(track, "name", getattr(track, "id", "Unknown"))
            text: str = f"[HLS] [{lang}] {name} | {mime or codecs}"
            return (0, 0, 0, text, track, "hls")
        else:
            # SubtitleTrack（MPD）
            track_id: int = getattr(track, "id", "Unknown")
            seg_count: int = len(getattr(track, "segment_urls", []))
            text: str = f"[MPD] [{lang}] {track_id} | {mime} | {seg_count} segs"
            return (0, 0, bw, text, track, "mpd")

    def _collect_all_candidates(self, target: int, track_type: TrackType) -> list[tuple[Any, str, int]]:
        """收集所有候選軌道"""
        candidates: list[tuple[Any, str, int]] = []
        if self.select_mode in {"hls", "all"} and self.hls_content:
            candidates.extend(self._collect_source_candidates(SourceType.HLS, target, track_type))
        if self.select_mode in {"mpd", "all"} and self.mpd_content:
            candidates.extend(self._collect_source_candidates(SourceType.MPD, target, track_type))
        return candidates

    def _collect_source_candidates(self, source: SourceType, target: int, track_type: TrackType) -> list[tuple[Any, str, int]]:
        """從特定來源收集候選軌道"""
        tracks: list = self._get_tracks(source, track_type)
        if not tracks:
            return []
        return [(track, source.value, track.bandwidth) for track in tracks if self._matches_target(track, target, track_type)]

    def _matches_target(self, track: Any, target: int, track_type: TrackType) -> bool:
        """檢查軌道是否符合目標值"""
        if track_type == TrackType.VIDEO:
            if hasattr(track, "resolution") and track.resolution:
                return target in track.resolution
            return track.width == target or track.height == target
        elif track_type == TrackType.AUDIO:
            if not track.bandwidth:
                return False
            track_kbps = track.bandwidth // 1000
            tolerance = target * 0.2 if hasattr(track, "id") else target * 0.1
            return abs(track_kbps - target) <= tolerance
        else:
            return False

    async def _fallback_audio_selection(self, target_kbps: int) -> tuple[HLSAudioTrack | MediaTrack | None, str | None]:
        """音訊回退選擇（選擇最高碼率）"""
        all_tracks: list[tuple[HLSAudioTrack | MediaTrack, str, int]] = []
        for source in [SourceType.HLS, SourceType.MPD]:
            if self.select_mode in {source.value, "all"}:
                tracks: list = self._get_tracks(source, TrackType.AUDIO)
                all_tracks.extend((t, source.value, t.bandwidth) for t in tracks if t.bandwidth)

        if all_tracks:
            best: tuple[HLSAudioTrack | MediaTrack, str, int] = max(all_tracks, key=lambda x: x[2])
            logger.warning(f"Using highest bitrate audio: [{best[1].upper()}] {best[2] // 1000:,} kbps")
            return best[0], best[1]

        logger.warning("Fail to auto select audio track, fallback to ask mode")
        if not self._collect_all_track_items(TrackType.AUDIO):
            raise ValueError("No audio tracks available")
        return await self._ask_track(TrackType.AUDIO)

    async def _apply_filters(
        self, track: Any | None, track_type: str | None
    ) -> tuple[Any | None, float | None, float | None]:
        """應用時間過濾到軌道（含字幕支援）"""
        if not track or not track_type:
            return track, None, None

        if track_type == "hls":
            if not hasattr(track, "segments") or not track.segments:
                return track, self.start_time, self.end_time

            segments, start, end = await self._filter_hls_segments(track)
            if not segments and track.segments:
                logger.warning("No HLS segments matched time range, using full track")
                return track, None, None

            segment_urls: list[str] = [s.url for s in segments]
            return replace(track, segments=segments, segment_urls=segment_urls), start, end

        else:  # mpd（MediaTrack 或 SubtitleTrack）
            if not hasattr(track, "segment_timeline") or not track.segment_timeline:
                return track, self.start_time, self.end_time

            seg_infos, start, end = await self._filter_mpd_segments(track)
            if not seg_infos and hasattr(track, "segments") and track.segments:
                logger.warning("No MPD segments matched time range, using full track")
                return track, None, None

            # 轉換為 MPD Segment 格式
            segments: list[SegmentInfo] = self._convert_to_mpd_segments(seg_infos, getattr(track, "timescale", 1) or 1)
            segment_urls: list[str] = [s.url for s in seg_infos]

            # SubtitleTrack 沒有 segments 欄位，用 hasattr 保護
            replace_kwargs: dict[str, Any] = {
                "segment_timeline": segments,
                "segment_urls": segment_urls,
            }
            if hasattr(track, "segments"):
                replace_kwargs["segments"] = segments

            return replace(track, **replace_kwargs), start, end

    async def _filter_hls_segments(
        self, track: HLSVariant | HLSAudioTrack
    ) -> tuple[list[HLSSegment], float | None, float | None]:
        """篩選 HLS 切片 使用累積時間和重疊邏輯"""
        if not hasattr(track, "segments") or not track.segments:
            return [], self.start_time, self.end_time

        segments: list[HLSSegment] = []
        cumulative: float = 0.0
        actual_start, actual_end = None, None

        for idx, seg in enumerate(track.segments):
            duration: float = getattr(seg, "duration", 0.0)
            seg_start: float = cumulative
            seg_end: float = cumulative + duration
            
            # 使用重疊邏輯判定
            if self._in_time_range(seg_start, seg_end):
                if actual_start is None:
                    actual_start: float = seg_start
                actual_end: float = seg_end
                segments.append(
                    HLSSegment(
                        url=getattr(seg, "url", ""),
                        duration=duration,
                        sequence=getattr(seg, "sequence", idx),
                    )
                )
            elif self.end_time and seg_start >= self.end_time + self.TIME_TOLERANCE:
                # 已超過結束時間(含容差),提早退出
                break

            cumulative = seg_end

        # 確保返回值合理
        if segments:
            actual_start: float = actual_start if actual_start is not None else 0.0
            actual_end: float = actual_end if actual_end is not None else cumulative
            logger.info(f"HLS: {len(segments)} segments ({actual_start:.2f}s → {actual_end:.2f}s, duration={actual_end - actual_start:.2f}s)")
        else:
            logger.warning("HLS: 0 segments matched time range")

        return segments, actual_start, actual_end

    async def _filter_mpd_segments(
        self, track: MediaTrack | SubtitleTrack
    ) -> tuple[list[SegmentInfo], float | None, float | None]:
        """篩選 MPD 切片 使用時間戳和重疊邏輯"""
        if not hasattr(track, "segment_timeline") or not track.segment_timeline:
            return [], self.start_time, self.end_time

        timeline: list = track.segment_timeline
        timescale: int = getattr(track, "timescale", 1) or 1
        url_map: dict[int, str] = self._build_url_map(track, timeline, timescale)

        segments: list[SegmentInfo] = []
        actual_start: float | None = None
        actual_end: float | None = None
        cumulative_time: float = 0.0 # 用於追蹤累積時間 (當 t 不存在時)

        for seg in timeline:
            # 獲取時間戳 (t 可能不存在,使用累積時間)
            seg_t: float = getattr(seg, "t", int(cumulative_time * timescale))
            seg_d: float = getattr(seg, "d", 0)
            seg_r: float = getattr(seg, "r", 0)
            repeat_count: int = (seg_r + 1) if seg_r >= 0 else 1

            for r in range(repeat_count):
                current_t: float = seg_t + r * seg_d
                current_start: float|int = current_t / timescale
                current_end: float|int = current_start + seg_d / timescale
                
                # 使用重疊邏輯判定
                if self._in_time_range(current_start, current_end):
                    if actual_start is None:
                        actual_start: float = current_start
                    actual_end: float = current_end
                    url: str = url_map.get(current_t) or self._generate_segment_url(track, current_t)
                    segments.append(
                        SegmentInfo(
                            url=url,
                            start_time=current_start,
                            duration=seg_d / timescale,
                            index=len(segments),
                        )
                    )
                elif self.end_time and current_start >= self.end_time + self.TIME_TOLERANCE:
                    # 已超過結束時間(含容差),提早退出
                    break

                cumulative_time = current_end

        # 確保返回值合理
        if segments:
            actual_start: float = actual_start if actual_start is not None else segments[0].start_time
            actual_end: float = actual_end if actual_end is not None else (segments[-1].start_time + segments[-1].duration)
            logger.info(f"MPD: {len(segments)} segments ({actual_start:.2f}s → {actual_end:.2f}s, duration={actual_end - actual_start:.2f}s)")
        else:
            logger.warning("MPD: 0 segments matched time range")

        return segments, actual_start, actual_end

    def _in_time_range(self, start: float, end: float) -> bool:
        """
        檢查時間段是否在過濾範圍內 - 使用重疊邏輯和容差

        重疊邏輯:
        - 分片結束時間 > 起始時間 (含容差)
        - 分片開始時間 < 結束時間 (含容差)
        """
        if self.start_time is not None:
            # 分片必須在起始時間之後結束 (含容差)
            if end < self.start_time - self.TIME_TOLERANCE:
                return False
        if self.end_time is not None:
            # 分片必須在結束時間之前開始 (含容差)
            if start > self.end_time + self.TIME_TOLERANCE:
                return False
        return True

    def _build_url_map(self, track: Any, timeline: list, timescale: int) -> dict[int, str]:
        """建置時間戳到 URL 的映射"""
        url_map: dict[int, str] = {}
        if not hasattr(track, "segment_urls") or not track.segment_urls:
            return url_map

        url_idx: int = 0
        cumulative_t: float = 0

        for seg in timeline:
            seg_t: float = getattr(seg, "t", cumulative_t)
            seg_d: float = getattr(seg, "d", 0)
            seg_r: float = getattr(seg, "r", 0)
            repeat_count: int = (seg_r + 1) if seg_r >= 0 else 1

            for r in range(repeat_count):
                current_t: float = seg_t + r * seg_d
                if url_idx < len(track.segment_urls):
                    url_map[current_t] = track.segment_urls[url_idx]
                    url_idx += 1

            cumulative_t: float = seg_t + repeat_count * seg_d

        return url_map

    def _generate_segment_url(self, track: Any, time: int) -> str:
        """生成 MPD segment URL (使用模板或回退)"""
        if hasattr(track, "segment_template") and track.segment_template:
            return (
                track.segment_template
                .replace("$RepresentationID$", str(track.id))
                .replace("$Time$", str(time))
                .replace("$Bandwidth$", str(track.bandwidth))
                .replace("$Number$", str(time))
            )
        return f"{track.id}/{time}.m4s"

    def _convert_to_mpd_segments(self, seg_infos: list[SegmentInfo], timescale: int) -> list[Segment]:
        """轉換 SegmentInfo 到 MPD Segment 格式"""
        return [Segment(t=int(s.start_time * timescale), d=int(s.duration * timescale), r=0) for s in seg_infos]

    def _update_paramstore(self, video_type: str | None, audio_type: str | None):
        """獲取 base URL"""
        paramstore._store.update(
            {
                "hls_video": video_type == "hls",
                "mpd_video": video_type == "mpd",
                "hls_audio": audio_type == "hls",
                "mpd_audio": audio_type == "mpd",
            }
        )

    def _get_base_url(self, video_type: str | None, audio_type: str | None) -> str:
        if video_type == "hls" or audio_type == "hls":
            return self.hls_content.base_url if self.hls_content else ""
        return self.mpd_content.base_url if self.mpd_content else ""

    def _log_filter_results(
        self,
        video: Any,
        audio: Any,
        start: float | None,
        end: float | None,
    ):
        """記錄過濾結果並檢查分片數量差異"""
        v_count: int = 0
        a_count: int = 0

        if video and hasattr(video, "segments"):
            v_count: int = len(video.segments)
            logger.info(f"Video: {v_count} segments selected")

        if audio and hasattr(audio, "segments"):
            a_count: int = len(audio.segments)
            logger.info(f"Audio: {a_count} segments selected")

        if start is not None and end is not None:
            logger.info(f"Time range: {start:.2f}s → {end:.2f}s (duration: {end - start:.2f}s)")

        if v_count > 0 and a_count > 0:
            diff: int = abs(v_count - a_count)
            if diff > 0:
                logger.info(f"{Color.fg('yellow')}Segment count difference: Video={v_count}, Audio={a_count} (±{diff} segments due to codec alignment, this is normal){Color.reset()}")
            else:
                logger.info(f"{Color.fg('green')}Segment counts match perfectly{Color.reset()}")

    def print_parsed_content(self):
        console: Console = Console(width=120)
        with console.capture() as capture:
            self._print_overview(console)
            for source in [SourceType.HLS, SourceType.MPD]:
                self._print_source_content(console, source)

        for line in capture.get().split("\n"):
            if line.strip():
                logger.info(line)

    def _print_overview(self, console: Console):
        for source, content in [
            (SourceType.HLS, self.hls_content),
            (SourceType.MPD, self.mpd_content),
        ]:
            if content:
                v = len(getattr(content, ("video_variants" if source == SourceType.HLS else "video_tracks"), []))
                a = len(content.audio_tracks or [])
                s = len(getattr(content, "subtitle_tracks", []) or [])
                symbol = "├─" if source == SourceType.HLS else "└─"
                color = "cyan" if source == SourceType.HLS else "blue"
                console.print(f"[{color}]{symbol} {source.value.upper()}[/{color}]: {v} video, {a} audio, {s} subtitle")
                console.print(f"{'│' if source == SourceType.HLS else ' '}  [white]{content.base_url}[/white]")

    def _print_source_content(self, console: Console, source: SourceType):
        content = self.hls_content if source == SourceType.HLS else self.mpd_content
        if not content:
            return

        color = "cyan" if source == SourceType.HLS else "blue"
        videos = content.video_variants if source == SourceType.HLS else content.video_tracks

        if videos:
            console.print(f"[bold {color}]{source.value.upper()} Video Tracks[/bold {color}]")
            sorted_videos = sorted(
                videos,
                key=lambda v: (getattr(v, "resolution", (0, 0))[1] if hasattr(v, "resolution") else getattr(v, "height", 0), getattr(v, "bandwidth", 0)),
                reverse=True,
            )
            for i, v in enumerate(sorted_videos, 1):
                self._print_track(console, i, v, True)

        if content.audio_tracks:
            console.print(f"[bold {color}]{source.value.upper()} Audio Tracks[/bold {color}]")
            sorted_audios = sorted(content.audio_tracks, key=lambda t: t.bandwidth or 0, reverse=True)
            for i, a in enumerate(sorted_audios, 1):
                self._print_track(console, i, a, False)

        subtitle_tracks: list = getattr(content, "subtitle_tracks", []) or []
        if subtitle_tracks:
            console.print(f"[bold {color}]{source.value.upper()} Subtitle Tracks[/bold {color}]")
            for i, sub in enumerate(subtitle_tracks, 1):
                self._print_subtitle_track(console, i, sub)
        sub_tracks: list = getattr(content, "sub_tracks", []) or []
        if sub_tracks:
            console.print(f"[bold {color}]{source.value.upper()} Subtitle Tracks[/bold {color}]")
            for i, sub in enumerate(sub_tracks, 1):
                self._print_subtitle_track(console, i, sub)

    def _print_track(self, console: Console, idx: int, track: Any, is_video: bool):
        if is_video:
            res = (
                f"{track.resolution[0]}x{track.resolution[1]}"
                if hasattr(track, "resolution") and track.resolution
                else f"{track.width}x{track.height}" if hasattr(track, "width") else "Unknown"
            )
            bw_val = getattr(track, "bandwidth", 0)
            bw_str = f"[green]{bw_val / 1_000_000:.2f}Mbps[/green] ([dim]{bw_val // 1000:,}kbps[/dim])" if bw_val else "[dim]N/A[/dim]"
            
            console.print(f"  {idx}. [cyan]Video: {res}[/cyan] {bw_str}")

            details = []
            attrs = [
                ("codecs", "Codec"), 
                ("frame_rate", "FPS"), 
                ("mime_type", "MIME")
            ]
            
            for attr, label in attrs:
                val = getattr(track, attr, None)
                if val:
                    val_str = f"[magenta]{val}[/magenta]" if label == "Codec" else str(val)
                    details.append(f"{label}: {val_str}")

            url = getattr(track, "playlist_url", getattr(track, "uri", getattr(track, "initialization_url", None)))
            if url:
                details.append(f"URI: [white]{url}[/white]")

            for i, d in enumerate(details):
                symbol = "└─" if i == len(details) - 1 else "├─"
                console.print(f"     {symbol} {d}")

        else:
            name = getattr(track, "name", getattr(track, "id", "Unknown"))
            lang = getattr(track, "language", "N/A")
            bw = getattr(track, "bandwidth", 0)
            bw_str = f"[green]{bw // 1000:.1f}kbps[/green]" if bw else "[dim]≒189kbps[/dim]"
            console.print(f"  {idx}. {name} [{lang}] {bw_str}")

            details = []
            for attr, label in [("codecs", "Codec"), ("mime_type", "MIME"), ("channels", "Channels")]:
                if hasattr(track, attr) and getattr(track, attr):
                    val = getattr(track, attr)
                    details.append(f"{label}: [magenta]{val}[/magenta]" if label == "Codec" else f"{label}: {val}")
            
            url = getattr(track, "playlist_url", getattr(track, "uri", getattr(track, "initialization_url", None)))
            if url:
                details.append(f"URI: [white]{url}[/white]")
                
            for i, d in enumerate(details):
                symbol = "└─" if i == len(details) - 1 else "├─"
                console.print(f"     {symbol} {d}")
                
    def _print_subtitle_track(self, console: Console, idx: int, track: Any):
        """列印字幕軌道詳情"""
        lang = getattr(track, "language", None) or "N/A"
        mime = getattr(track, "mime_type", "N/A")
        codecs = getattr(track, "codecs", None) or "N/A"
        seg_count = len(getattr(track, "segment_urls", []))
        track_id = getattr(track, "id", "Unknown")
        console.print(
            f" [white]{idx:2}.[/white] "
            f"[[orchid]{lang}[/orchid]] "
            f"[cyan]{track_id}[/cyan] | "
            f"[orange1]{mime}[/orange1] | "
            f"codec=[green_yellow]{codecs}[/green_yellow] | "
            f"[medium_spring_green]{seg_count} segs[/medium_spring_green]"
        )

        uri = getattr(track, "init_url", getattr(track, "uri", None))
        if uri:
            console.print(f"      [gray]└─ URI:[/gray][white]{uri}[/white]")