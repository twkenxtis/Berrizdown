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
from berrizdown.unit.clean_files import CleanFiles

logger = setup_logging("reName", "violet")


class SUCCESS:
    def __init__(
        self,
        dl_obj: object,
        output_dir: Path,
        public_info: PublicInfo,
        playback_info: PlaybackInfo,
        custom_community_name: str,
        community_name: str,
        decryption_key: list[str] | None,
    ) -> None:
        self.dl_obj: object = dl_obj
        self.base_dir: Path = output_dir
        self._public_info: PublicInfo = public_info
        self._playback_info: PlaybackInfo = playback_info
        self._filename_sanitizer: FilenameSanitizer = FilenameSanitizer.sanitize_filename

        self.artis_list: list[dict[str, str | None]] = self.publicinfo.artists
        self.community_name: str = community_name or custom_community_name
        self.custom_community_name: str = custom_community_name or community_name
        self.get_artis: str = get_artis_list(self.artis_list)
        self.path: Path = Path.cwd() / self.base_dir / f"temp_mux_{self.publicinfo.media_id}.{container}"
        self.time_str: str = self.FDT.vod_live_time_str()
        self.decryption_key: list[str] = decryption_key

        if self.get_artis == self.community_name or self.get_artis == self.custom_community_name:
            artis_name = self.get_artis.lower()
        else:
            artis_name = self.get_artis
        self.artis_name: str = artis_name

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
    ) -> tuple[str, bool]:
        """處理下載成功後的邏輯 下載縮圖 混流重新命名與清理檔案"""
        if success or paramstore.get("skip_merge") is True:
            mux_succeeded: bool = await self.run_mux()
            final_video_name_with_p2p, mux_succeeded = await self._derive_outcome_label(mux_succeeded)
            if final_video_name_with_p2p == "":
                mux_succeeded: bool = True
                if paramstore.get("skip_merge"):
                    final_video_name_with_p2p: str = "[ User choese SKIP MERGE ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
            await self._maybe_cleanup_artifacts(mux_succeeded)
            return final_video_name_with_p2p, mux_succeeded

    async def run_mux(self) -> bool:
        if paramstore.get("subs_only") is True:
            return True
        muxer: FFmpegMuxer = FFmpegMuxer(self.path, self.playbackinfo.is_drm, self.dl_obj, self.decryption_key)
        return await muxer.mux_main()

    async def _derive_outcome_label(self, mux_succeeded: bool, final_video_name_with_p2p: str = "") -> tuple[str, bool]:
        if mux_succeeded is True and paramstore.get("nodl") is not True:
            if self.path.exists():
                final_video_name_with_p2p: str = await self.re_name()
        elif paramstore.get("nodl") is True:
            final_video_name_with_p2p: str = "[ SKIP-DL ]"
        elif paramstore.get("subs_only") is True:
            final_video_name_with_p2p: str = "[ SUBS ONLY ]"
        elif paramstore.get("slice_path_fail") is True:
            final_video_name_with_p2p: str = "[ Fail to create folder for download slice ]"
        elif paramstore.get("skip_merge") is True and mux_succeeded is False:
            logger.info(f"{Color.fg('yellow')}Skipping file cleaning, keep segments after done{Color.reset()}")
        elif paramstore.get("skip_mux") is True and mux_succeeded is False:
            final_video_name_with_p2p: str = "[ User choese SKIP MUX ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
        elif paramstore.get("no_key_drm") is True:
            final_video_name_with_p2p: str = "[ DRM key not found ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
        else:
            logger.warning("Mux failed, check console output for details")
            final_video_name_with_p2p: str = "[ Mux failed ] " + f"{Color.bg('ruby')}Keep all segments in folder{Color.reset()}"
            mux_succeeded: bool = False
        return final_video_name_with_p2p, mux_succeeded

    async def _maybe_cleanup_artifacts(self, mux_succeeded: bool) -> None:
        if paramstore.get("clean_dl") is not False and mux_succeeded is True:
            await CleanFiles(self.dl_obj, self.base_dir, self.decryption_key).clean_file()
        else:
            logger.info(f"{Color.fg('yellow')}Skipping file cleaning, keep segments after done{Color.reset()}")

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
        
        await aios.rename(self.path, Path(self.base_dir).parent / filename)
        return filename