import asyncio
import os
import shutil
from functools import cached_property

import aiofiles.os as aios

from berrizdown.lib.__init__ import (
    File_date_time_formact,
    OutputFormatter,
    container,
    get_artis_list,
)
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.mux.mux import FFmpegMuxer
from berrizdown.lib.name_metadata import meta_name
from berrizdown.lib.path import Path
from berrizdown.lib.rename.extract_video_info import extract_video_info
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.PlaybackInfo import PlaybackInfo
from berrizdown.static.PublicInfo import PublicInfo
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("reName", "violet")


class SUCCESS:
    def __init__(
        self,
        output_dir: Path,
        public_info: PublicInfo,
        playback_info: PlaybackInfo,
        custom_community_name: str,
        community_name: str,
    ) -> None:
        self.base_dir: Path = output_dir
        self._public_info = public_info
        self._playback_info = playback_info
        self._filename_sanitizer = FilenameSanitizer.sanitize_filename

        self.artis_list: list[dict[str, str | None]] = self.publicinfo.artists
        self.community_name: str = community_name or custom_community_name
        self.custom_community_name: str = custom_community_name or community_name
        self.get_artis = get_artis_list(self.artis_list)
        self.tempname: str = f"temp_mux_{self.publicinfo.media_id}.{container}"
        self.path: Path = Path.cwd() / self.base_dir / self.tempname
        self.time_str: str = self.FDT.vod_live_time_str()

        if self.get_artis == self.community_name or self.get_artis == self.custom_community_name:
            artis_name = self.get_artis.lower()
        else:
            artis_name = self.get_artis
        self.artis_name = artis_name

    @cached_property
    def FDT(self) -> object:
        return File_date_time_formact(self.publicinfo, "VOD_LIVE")

    @cached_property
    def publicinfo(self) -> PublicInfo:
        return self._public_info

    @cached_property
    def playbackinfo(self) -> PlaybackInfo:
        return self._playback_info

    @cached_property
    def filenameSanitizer(self):
        return self._filename_sanitizer

    async def when_success(
        self,
        success: bool,
        decryption_key: bytes | str | None,
    ) -> str | bool:
        """處理下載成功後的邏輯：下載縮圖、混流、重新命名與清理檔案"""
        if success or paramstore.get("skip_merge") is True:
            logger.info(f"{Color.fg('light_gray')}Video file: {Color.fg('mist')}{self.base_dir / f'video.{container}'}{Color.reset()}")
            logger.info(f"{Color.fg('light_gray')}Audio file: {Color.fg('mist')}{self.base_dir / f'audio.{container}'}{Color.reset()}")
            return await self.handle_mux_status(decryption_key)

    async def handle_mux_status(self, decryption_key: bytes | str | None):
        # Orchestrates the mux pipeline: run → decide outcome → cleanup → finalize
        outcome_label, mux_succeeded = await self._run_mux(decryption_key)
        outcome_label, mux_succeeded = await self._derive_outcome_label(outcome_label, mux_succeeded)
        await self._maybe_cleanup_artifacts(decryption_key, mux_succeeded)
        outcome_label, mux_succeeded = self._finalize_outcome(outcome_label, mux_succeeded)
        return outcome_label, mux_succeeded

    async def _run_mux(self, decryption_key: bytes | str | None) -> tuple[str, bool]:
        muxer: FFmpegMuxer = FFmpegMuxer(self.base_dir, self.playbackinfo.is_drm, decryption_key)
        outcome_label = ""
        mux_succeeded = await muxer.mux_main(self.path)
        return outcome_label, mux_succeeded

    async def _derive_outcome_label(self, outcome_label: str, mux_succeeded: bool) -> tuple[str, bool]:
        if mux_succeeded is True and paramstore.get("nodl") is not True:
            if os.path.exists(self.path):
                outcome_label = await self.re_name()
            else:
                pass
        elif paramstore.get("nodl") is True:
            outcome_label = "[ SKIP-DL ]"
        elif paramstore.get("slice_path_fail") is True:
            outcome_label = "[ Fail to create folder for download slice ]"
        elif paramstore.get("skip_merge") is True and mux_succeeded is False:
            logger.info(f"{Color.fg('yellow')}Skipping file cleaning, keep segments after done{Color.reset()}")
        elif paramstore.get("skip_mux") is True and mux_succeeded is False:
            outcome_label = "[ User choese SKIP MUX ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
        elif paramstore.get("no_key_drm") is True:
            outcome_label = "[ DRM key not found ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
        else:
            logger.warning("Mux failed, check console output for details")
            outcome_label = "[ Mux failed ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
            mux_succeeded = False
        return outcome_label, mux_succeeded

    async def _maybe_cleanup_artifacts(self, decryption_key: bytes | str | None, mux_succeeded: bool) -> None:
        if paramstore.get("clean_dl") is not False and mux_succeeded is True:
            await self.clean_file(decryption_key)
        else:
            logger.info(f"{Color.fg('yellow')}Skipping file cleaning, keep segments after done{Color.reset()}")

    def _finalize_outcome(self, outcome_label: str, mux_succeeded: bool) -> tuple[str, bool]:
        match outcome_label:
            case "":
                mux_succeeded = True
                if paramstore.get("skip_merge"):
                    outcome_label = "[ User choese SKIP MERGE ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
            case _:
                pass
        return outcome_label, mux_succeeded

    async def clean_file(self, had_drm: bytes | str | None) -> None:
        """清理下載過程中的暫存檔案、加密檔案和暫存目錄"""
        base_dir: Path = self.base_dir
        if os.path.exists(base_dir):
            file_paths: list[Path] = []
            # Files to delete
            if had_drm is None:
                file_paths = [
                    base_dir / f"video.{container}",
                    base_dir / f"audio.{container}",
                ]
            else:
                file_paths = [
                    base_dir / f"video_decrypted.{container}",
                    base_dir / f"video.{container}",
                    base_dir / f"audio_decrypted.{container}",
                    base_dir / f"audio.{container}",
                ]

            for fp in file_paths:
                try:
                    await asyncio.to_thread(fp.unlink)
                    logger.info(f"Removed file: {Color.fg('mist')}{fp}{Color.reset()}")
                except FileNotFoundError:
                    logger.info(f"File not found, skipping: {fp}")
                except Exception as e:
                    logger.error(f"Error removing file {fp}: {e}")

            for subfolder in ["audio", "video"]:
                dir_path: Path = base_dir / subfolder
                try:
                    await asyncio.to_thread(shutil.rmtree, dir_path)
                    logger.info(f"Force-removed directory: {Color.fg('mist')}{dir_path}{Color.reset()}")
                except FileNotFoundError:
                    logger.info(f"Directory not found, skipping: {dir_path}")
                except Exception as e:
                    logger.error(f"Error force-removing directory {dir_path}: {e}")

    async def re_name(self) -> str:
        """根據影片元數據和命名規則重新命名最終的 MP4 檔案"""
        video_codec: str
        video_quality_label: str
        video_audio_codec: str
        if paramstore.get("ffprobe_path_ok") is True:
            video_codec, video_quality_label, video_audio_codec = await extract_video_info(self.path)
        else:
            video_codec, video_quality_label, video_audio_codec = "unknow_codec", "unknown_resolution", "unknown_audio_codec"
            
        video_meta: dict[str, str] = meta_name(
            self.time_str,
            self.publicinfo.title,
            self.community_name,
            self.artis_name,
        )
        
        video_meta["quality"] = video_quality_label
        video_meta["video"] = video_codec
        video_meta["audio"] = video_audio_codec
        filename_formact: str = CFG["output_template"]["video"]
        
        if video_codec == "{video}":
            filename_formact = filename_formact.replace(".{quality}", "")
            filename_formact = filename_formact.replace(".{video}", "")
        if video_audio_codec == "{audio}":
            filename_formact = filename_formact.replace(".{audio}", "")
            
        filename = OutputFormatter(filename_formact).format(video_meta) + f".{container}"
        
        # 重新命名並移動到上級目錄
        await aios.rename(self.path, Path(self.base_dir).parent / filename)
        return filename
