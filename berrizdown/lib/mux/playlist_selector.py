import sys
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from InquirerPy import inquirer
from rich.console import Console

from berrizdown.lib.mux.parse_hls import HLSAudioTrack, HLSContent, HLSSegment, HLSVariant
from berrizdown.lib.mux.parse_mpd import MediaTrack, MPDContent, Segment
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("playlist_selector", "periwinkle")


class TrackType(Enum):
    VIDEO = "video"
    AUDIO = "audio"


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
        self.hls_content = hls_content
        self.mpd_content = mpd_content
        self.select_mode = select_mode.lower()
        self.start_time = self._validate_time(start_time, "start_time")
        self.end_time = self._validate_time(end_time, "end_time")
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
            start_str = f"{self.start_time:.2f}s" if self.start_time is not None else "START"
            end_str = f"{self.end_time:.2f}s" if self.end_time is not None else "END"
            logger.info(f"{Color.fg('cyan')}Time range filter enabled: {start_str} → {end_str}. Minor segment count differences between tracks are expected due to codec alignment.{Color.reset()}")

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
    ) -> SelectedContent:
        """選擇視訊和音訊軌道"""
        # 選擇軌道
        selected_video, video_type = await self._select_single_track(v_resolution_choice, TrackType.VIDEO, video_codec)
        selected_audio, audio_type = await self._select_single_track(a_resolution_choice, TrackType.AUDIO)

        # 更新 paramstore
        self._update_paramstore(video_type, audio_type)
        content_type = video_type if video_type == audio_type else "mixed"
        base_url = self._get_base_url(video_type, audio_type)

        # 應用時間過濾
        actual_start, actual_end = None, None
        if self.start_time is not None or self.end_time is not None:
            logger.info(f"Applying time filter: {self.start_time} → {self.end_time}")

            # 分別過濾並獲取實際時間範圍
            selected_video, v_start, v_end = await self._apply_filters(selected_video, video_type)
            selected_audio, a_start, a_end = await self._apply_filters(selected_audio, audio_type)

            # 使用影像時間作為基準對GOP
            actual_start = v_start if v_start is not None else a_start
            actual_end = v_end if v_end is not None else a_end

            self._log_filter_results(selected_video, selected_audio, actual_start, actual_end)
        else:
            logger.info("No time filtering applied")

        return SelectedContent(
            video_track=selected_video,
            audio_track=selected_audio,
            content_type=content_type or "unknown",
            base_url=base_url,
            start_time=actual_start,
            end_time=actual_end,
        )

    async def _select_single_track(self, choice: str, track_type: TrackType, codec: str | None = None) -> tuple[HLSVariant | HLSAudioTrack | MediaTrack | None, str | None]:
        """統一軌道選擇"""
        if choice.lower() == "none":
            return None, None

        if choice.lower() in {"ask", "as"}:
            return await self._ask_track(track_type)

        return await self._auto_select_track(int(choice), track_type)

    async def _ask_track(self, track_type: TrackType) -> tuple[HLSVariant | HLSAudioTrack | MediaTrack | None, str | None]:
        """交互式選擇軌道"""
        items = self._collect_all_track_items(track_type)

        if not items:
            logger.warning(f"No {track_type.value} tracks available")
            return None, None

        # 過濾掉空的 tuple 並使用安全的排序
        items = [item for item in items if len(item) >= 6]

        # None 換 0 進行排序
        items.sort(
            key=lambda x: (
                x[0] if x[0] is not None else 0,
                x[1] if x[1] is not None else 0,
                x[2] if x[2] is not None else 0,
            )
        )

        choices = [item[3] for item in items]
        track_map = {item[3]: (item[4], item[5]) for item in items}

        try:
            answer = await inquirer.select(
                message=f"Choose {track_type.value} track [{self.select_mode.upper()}]:",
                choices=choices,
                default=choices[-1],
            ).execute_async()
        except KeyboardInterrupt:
            sys.exit(0)
        return track_map[answer]

    async def _auto_select_track(self, target: int, track_type: TrackType) -> tuple[HLSVariant | HLSAudioTrack | MediaTrack | None, str | None]:
        """自動選擇軌道"""
        candidates = self._collect_all_candidates(target, track_type)

        if not candidates:
            if track_type == TrackType.AUDIO:
                return await self._fallback_audio_selection(target)
            raise ValueError(f"{track_type.value} track not found for target {target}")

        best = max(candidates, key=lambda x: x[2])
        logger.info(f"Auto-select {Color.fg('sea_green')}{track_type.value}: {Color.reset()}{Color.fg('light_gray')}[{best[1].upper()}] @ {best[2] // 1000:,} kbps{Color.reset()}")
        return best[0], best[1]

    def _collect_all_track_items(self, track_type: TrackType) -> list[tuple]:
        """收集所有軌道項目"""
        items = []

        if self.select_mode in {"hls", "all"} and self.hls_content:
            items.extend(self._collect_source_items(SourceType.HLS, track_type))

        if self.select_mode in {"mpd", "all"} and self.mpd_content:
            items.extend(self._collect_source_items(SourceType.MPD, track_type))

        return items

    def _collect_source_items(self, source: SourceType, track_type: TrackType) -> list[tuple]:
        """從特定來源收集軌道項目"""
        tracks = self._get_tracks(source, track_type)
        if not tracks:
            return []

        items = [self._format_track_item(track, source, track_type) for track in tracks]

        # 過濾 None
        return [item for item in items if item is not None]

    def _get_tracks(self, source: SourceType, track_type: TrackType) -> list:
        """取得指定來源和類型的軌道列表"""
        content = self.hls_content if source == SourceType.HLS else self.mpd_content
        if not content:
            return []

        if track_type == TrackType.VIDEO:
            return content.video_variants if source == SourceType.HLS else content.video_tracks
        else:
            return content.audio_tracks

    def _format_track_item(self, track: Any, source: SourceType, track_type: TrackType) -> tuple | None:
        """格式化單一軌道項目"""
        if track_type == TrackType.VIDEO:
            return self._format_video_item(track, source)
        return self._format_audio_item(track, source)

    def _format_video_item(self, track: Any, source: SourceType) -> tuple | None:
        """影像軌轉換"""
        if source == SourceType.HLS:
            if not hasattr(track, "resolution") or not track.resolution:
                return None
            w, h = track.resolution
            bw_kbps = track.bandwidth // 1000
            codec = track.codecs or "N/A"
            text = f"[HLS] {w}x{h} | {bw_kbps:,} kbps | {codec}"
            return (h, w, track.bandwidth, text, track, "hls")

        elif source == SourceType.MPD:
            if not track.width or not track.height:
                return None
            bw_kbps = track.bandwidth // 1000
            text = f"[MPD] {track.width}x{track.height} | {bw_kbps:,} kbps | {track.codecs}"
            return (track.height, track.width, track.bandwidth, text, track, "mpd")

        return None

    def _format_audio_item(self, track: Any, source: SourceType) -> tuple | None:
        """音訊軌轉換"""
        lang = getattr(track, "language", "N/A")
        bw = getattr(track, "bandwidth", 0)

        if source == SourceType.HLS:
            name = getattr(track, "name", "Unknown")
            bw_str = f"{bw // 1000}kbps" if bw else "≒189kbps"
            text = f"[HLS] [{lang}] {name} | {bw_str}"
            return (bw, 0, 0, text, track, "hls")

        else:  # MPD
            if not hasattr(track, "id"):
                return None
            bw_kbps = bw // 1000
            rate = getattr(track, "audio_sampling_rate", None)
            rate_str = f"{rate}Hz" if rate else "N/A"
            text = f"[MPD] [{lang}] {track.id} | {bw_kbps}kbps / {rate_str}"
            return (bw, 0, 0, text, track, "mpd")

    def _collect_all_candidates(self, target: int, track_type: TrackType) -> list[tuple[Any, str, int]]:
        """收集所有候選軌道"""
        candidates = []

        if self.select_mode in {"hls", "all"} and self.hls_content:
            candidates.extend(self._collect_source_candidates(SourceType.HLS, target, track_type))

        if self.select_mode in {"mpd", "all"} and self.mpd_content:
            candidates.extend(self._collect_source_candidates(SourceType.MPD, target, track_type))

        return candidates

    def _collect_source_candidates(self, source: SourceType, target: int, track_type: TrackType) -> list[tuple[Any, str, int]]:
        """從特定來源收集候選軌道"""
        tracks = self._get_tracks(source, track_type)
        if not tracks:
            return []

        return [(track, source.value, track.bandwidth) for track in tracks if self._matches_target(track, target, track_type)]

    def _matches_target(self, track: Any, target: int, track_type: TrackType) -> bool:
        """檢查軌道是否符合目標值"""
        if track_type == TrackType.VIDEO:
            if hasattr(track, "resolution") and track.resolution:
                return target in track.resolution
            return track.width == target or track.height == target
        else:  # AUDIO
            if not track.bandwidth:
                return False
            track_kbps = track.bandwidth // 1000
            tolerance = target * 0.2 if hasattr(track, "id") else target * 0.1
            return abs(track_kbps - target) <= tolerance

    async def _fallback_audio_selection(self, target_kbps: int) -> tuple[HLSAudioTrack | MediaTrack | None, str | None]:
        """音訊回退選擇（選擇最高碼率）"""
        all_tracks = []

        for source in [SourceType.HLS, SourceType.MPD]:
            if self.select_mode in {source.value, "all"}:
                tracks = self._get_tracks(source, TrackType.AUDIO)
                all_tracks.extend((t, source.value, t.bandwidth) for t in tracks if t.bandwidth)

        if all_tracks:
            best = max(all_tracks, key=lambda x: x[2])
            logger.warning(f"Using highest bitrate audio: [{best[1].upper()}] {best[2] // 1000:,} kbps")
            return best[0], best[1]
        
        logger.warning("Fail to auto select audio track, fallback to ask mode")
        
        if not self._collect_all_track_items(TrackType.AUDIO):
            raise ValueError("No audio tracks available")
        else:
            return await self._ask_track(TrackType.AUDIO)

    async def _apply_filters(self, track: Any | None, track_type: str | None) -> tuple[Any | None, float | None, float | None]:
        """應用時間過濾到軌道"""
        if not track or not track_type:
            return track, None, None

        if track_type == "hls":
            segments, start, end = await self._filter_hls_segments(track)

            # 檢查是否有有效分片
            if not segments and hasattr(track, "segments") and track.segments:
                logger.warning("No HLS segments matched time range, using full track")
                return track, None, None

            # 更新 HLS 軌道
            segment_urls = [s.url for s in segments]
            return (
                replace(track, segments=segments, segment_urls=segment_urls),
                start,
                end,
            )

        else:  # mpd
            seg_infos, start, end = await self._filter_mpd_segments(track)

            # 檢查是否有有效分片
            if not seg_infos and hasattr(track, "segments") and track.segments:
                logger.warning("No MPD segments matched time range, using full track")
                return track, None, None

            # 轉換為 MPD Segment 格式
            segments = self._convert_to_mpd_segments(seg_infos, track.timescale or 1)
            segment_urls = [s.url for s in seg_infos]

            return (
                replace(
                    track,
                    segments=segments,
                    segment_timeline=segments,
                    segment_urls=segment_urls,
                ),
                start,
                end,
            )

    async def _filter_hls_segments(self, track: HLSVariant | HLSAudioTrack) -> tuple[list[HLSSegment], float | None, float | None]:
        """篩選 HLS 切片 - 使用累積時間和重疊邏輯"""
        if not hasattr(track, "segments") or not track.segments:
            return [], self.start_time, self.end_time

        segments = []
        cumulative = 0.0
        actual_start, actual_end = None, None

        for idx, seg in enumerate(track.segments):
            duration = getattr(seg, "duration", 0.0)
            seg_start = cumulative
            seg_end = cumulative + duration

            # 使用重疊邏輯判定
            if self._in_time_range(seg_start, seg_end):
                if actual_start is None:
                    actual_start = seg_start
                actual_end = seg_end

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
            actual_start = actual_start if actual_start is not None else 0.0
            actual_end = actual_end if actual_end is not None else cumulative
            logger.info(f"HLS: {len(segments)} segments ({actual_start:.2f}s → {actual_end:.2f}s, duration={actual_end - actual_start:.2f}s)")
        else:
            logger.warning("HLS: 0 segments matched time range")

        return segments, actual_start, actual_end

    async def _filter_mpd_segments(self, track: MediaTrack) -> tuple[list[SegmentInfo], float | None, float | None]:
        """篩選 MPD 切片 - 使用時間戳和重疊邏輯"""
        if not hasattr(track, "segment_timeline") or not track.segment_timeline:
            return [], self.start_time, self.end_time

        timeline = track.segment_timeline
        timescale = getattr(track, "timescale", 1)
        url_map = self._build_url_map(track, timeline, timescale)

        segments = []
        actual_start, actual_end = None, None
        cumulative_time = 0.0  # 用於追蹤累積時間 (當 t 不存在時)

        for idx, seg in enumerate(timeline):
            # 獲取時間戳 (t 可能不存在,使用累積時間)
            seg_t = getattr(seg, "t", int(cumulative_time * timescale))
            seg_d = getattr(seg, "d", 0)
            seg_r = getattr(seg, "r", 0)

            repeat_count = (seg_r + 1) if seg_r >= 0 else 1

            for r in range(repeat_count):
                current_t = seg_t + r * seg_d
                current_start = current_t / timescale
                current_end = current_start + seg_d / timescale

                # 使用重疊邏輯判定
                if self._in_time_range(current_start, current_end):
                    if actual_start is None:
                        actual_start = current_start
                    actual_end = current_end

                    url = url_map.get(current_t) or self._generate_segment_url(track, current_t)
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
            actual_start = actual_start if actual_start is not None else segments[0].start_time
            actual_end = actual_end if actual_end is not None else (segments[-1].start_time + segments[-1].duration)
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

    def _build_url_map(self, track: MediaTrack, timeline, timescale: int) -> dict[int, str]:
        """建置時間戳到 URL 的映射"""
        url_map = {}
        if not hasattr(track, "segment_urls") or not track.segment_urls:
            return url_map

        url_idx = 0
        cumulative_t = 0

        for seg in timeline:
            seg_t = getattr(seg, "t", cumulative_t)
            seg_d = getattr(seg, "d", 0)
            seg_r = getattr(seg, "r", 0)

            repeat_count = (seg_r + 1) if seg_r >= 0 else 1

            for r in range(repeat_count):
                current_t = seg_t + r * seg_d
                if url_idx < len(track.segment_urls):
                    url_map[current_t] = track.segment_urls[url_idx]
                    url_idx += 1

            cumulative_t = seg_t + repeat_count * seg_d

        return url_map

    def _generate_segment_url(self, track: MediaTrack, time: int) -> str:
        """生成 MPD segment URL (使用模板或回退)"""
        if hasattr(track, "segment_template") and track.segment_template:
            return track.segment_template.replace("$RepresentationID$", str(track.id)).replace("$Time$", str(time)).replace("$Bandwidth$", str(track.bandwidth)).replace("$Number$", str(time))
        return f"{track.id}/{time}.m4s"

    def _convert_to_mpd_segments(self, seg_infos: list[SegmentInfo], timescale: int) -> list[Segment]:
        """轉換 SegmentInfo 到 MPD Segment 格式"""
        return [Segment(t=int(s.start_time * timescale), d=int(s.duration * timescale), r=0) for s in seg_infos]

    def _update_paramstore(self, video_type: str | None, audio_type: str | None):
        """更新 paramstore 狀態"""
        paramstore._store.update(
            {
                "hls_video": video_type == "hls",
                "mpd_video": video_type == "mpd",
                "hls_audio": audio_type == "hls",
                "mpd_audio": audio_type == "mpd",
            }
        )

    def _get_base_url(self, video_type: str | None, audio_type: str | None) -> str:
        """獲取 base URL"""
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
        v_count = 0
        a_count = 0

        if video and hasattr(video, "segments"):
            v_count = len(video.segments)
            logger.info(f"Video: {v_count} segments selected")

        if audio and hasattr(audio, "segments"):
            a_count = len(audio.segments)
            logger.info(f"Audio: {a_count} segments selected")

        # 記錄時間範圍
        if start is not None and end is not None:
            logger.info(f"Time range: {start:.2f}s → {end:.2f}s (duration: {end - start:.2f}s)")

        # 檢查並記錄分片數量差異
        if v_count > 0 and a_count > 0:
            diff = abs(v_count - a_count)
            if diff > 0:
                logger.info(f"{Color.fg('yellow')}Segment count difference: Video={v_count}, Audio={a_count} (±{diff} segments due to codec alignment, this is normal){Color.reset()}")
            else:
                logger.info(f"{Color.fg('green')}Segment counts match perfectly{Color.reset()}")

    def print_parsed_content(self):
        """列印解析的內容"""
        console = Console(width=120)
        with console.capture() as capture:
            self._print_overview(console)
            for source in [SourceType.HLS, SourceType.MPD]:
                self._print_source_content(console, source)

        for line in capture.get().split("\n"):
            if line.strip():
                logger.info(line)

    def _print_overview(self, console: Console):
        """列印概覽"""
        for source, content in [
            (SourceType.HLS, self.hls_content),
            (SourceType.MPD, self.mpd_content),
        ]:
            if content:
                v = len(
                    getattr(
                        content,
                        ("video_variants" if source == SourceType.HLS else "video_tracks"),
                        [],
                    )
                )
                a = len(content.audio_tracks or [])
                symbol = "├─" if source == SourceType.HLS else "└─"
                color = "cyan" if source == SourceType.HLS else "blue"
                console.print(f"[{color}]{symbol} {source.value.upper()}[/{color}]: {v} video, {a} audio")
                console.print(f"{'│' if source == SourceType.HLS else ' '}  [white]{content.base_url}[/white]")

    def _print_source_content(self, console: Console, source: SourceType):
        """列印特定來源的內容"""
        content = self.hls_content if source == SourceType.HLS else self.mpd_content
        if not content:
            return

        color = "cyan" if source == SourceType.HLS else "blue"

        # Video
        videos = content.video_variants if source == SourceType.HLS else content.video_tracks
        if videos:
            console.print(f"\n[bold {color}]{source.value.upper()} Video Tracks[/bold {color}]")
            sorted_videos = sorted(
                videos,
                key=lambda v: (
                    (getattr(v, "resolution", (0, 0))[1] if hasattr(v, "resolution") else getattr(v, "height", 0)),
                    getattr(v, "bandwidth", 0),
                ),
                reverse=True,
            )
            for i, v in enumerate(sorted_videos, 1):
                self._print_track(console, i, v, True)

        # Audio
        if content.audio_tracks:
            console.print(f"\n[bold {color}]{source.value.upper()} Audio Tracks[/bold {color}]")
            sorted_audios = sorted(content.audio_tracks, key=lambda t: t.bandwidth or 0, reverse=True)
            for i, a in enumerate(sorted_audios, 1):
                self._print_track(console, i, a, False)

    def _print_track(self, console: Console, idx: int, track: Any, is_video: bool):
        """單軌打印"""
        if is_video:
            res = f"{track.resolution[0]}x{track.resolution[1]}" if hasattr(track, "resolution") and track.resolution else (f"{track.width}x{track.height}" if hasattr(track, "width") else "N/A")
            bw = f"{track.bandwidth / 1_000_000:.2f}Mbps ({track.bandwidth / 1_000:,.0f}kbps)"
            console.print(f"  [{idx}] [cyan]{res}[/cyan] · [green]{bw}[/green]")
        else:
            name = getattr(track, "name", getattr(track, "id", "Unknown"))
            lang = getattr(track, "language", "N/A")
            bw = getattr(track, "bandwidth", 0)
            bw_str = f"[green]{bw / 1_000:.1f}kbps[/green]" if bw else "[dim]~189kbps[/dim]"
            console.print(f"  [{idx}] {name} · [{lang}] · {bw_str}")

        details = []
        for attr, label in [
            ("codecs", "Codec"),
            ("mime_type", "MIME"),
            ("channels", "Channels"),
        ]:
            if hasattr(track, attr) and getattr(track, attr):
                val = getattr(track, attr)
                details.append((label, f"[magenta]{val}[/magenta]" if label == "Codec" else val))

        url = getattr(
            track,
            "playlist_url",
            getattr(track, "uri", getattr(track, "initialization_url", None)),
        )
        if url:
            details.append(("URI", f"[white]{url}[/white]"))

        for i, (label, val) in enumerate(details):
            symbol = "└─" if i == len(details) - 1 else "├─"
            console.print(f"      {symbol} {label}: {val}" if label != "URI" else f"      {symbol} {val}")
