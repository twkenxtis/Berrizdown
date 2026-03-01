import asyncio
import os
import socket
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Never, Optional, Union

import aiohttp
import aiofiles
from aiohttp import ClientTimeout, ClientResponse

from berrizdown.lib.__init__ import use_proxy
from berrizdown.lib.__init__ import container
from berrizdown.lib.Proxy import Proxy
from berrizdown.lib.load_yaml_config import CFG, ConfigLoader
from berrizdown.lib.mux.merge import MERGE
from berrizdown.lib.mux.parse_hls import HLS_Paser, HLSContent, HLSSubTrack, HLSVariant
from berrizdown.lib.mux.parse_mpd import MediaTrack, MPDContent, MPDParser, SubtitleTrack
from berrizdown.lib.mux.playlist_selector import PlaylistSelector
from berrizdown.lib.path import Path
from berrizdown.lib.processbar.processbar import MultiTrackProgressManager
from berrizdown.lib.rename.rename import SUCCESS
from berrizdown.lib.save_json_data import save_json_data
from berrizdown.lib.video_folder import Video_folder
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.PlaybackInfo import PlaybackInfo
from berrizdown.static.PublicInfo import PublicInfo
from berrizdown.unit.__init__ import USERAGENT, FilenameSanitizer
from berrizdown.unit.date.date import video_start2end_time
from berrizdown.unit.sub.subprocess import SubtitleProcessor
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("download", "peach")


progress_manager = MultiTrackProgressManager()



async def _get_random_proxy() -> str:
    """Select a random proxy from the proxy list, throttled to one call per second."""
    if use_proxy is not True:
        return ""
    
    raw: str = random.choice(Proxy._load_proxies())
    raw = raw.strip().rstrip(",")
    try:
        host, port, user, password = raw.split(":", maxsplit=3)
        proxy_url: str = f"http://{user}:{password}@{host}:{port}"
    except ValueError:
        proxy_url: str = raw
    return proxy_url


@dataclass
class DownloadObjection:
    video: Path = Path("")
    audio: Path = Path("")
    subtitle: dict[Union["HLSSubTrack", "SubtitleTrack"], Path] = field(default_factory=dict)
    task_info: Optional[object] = None


@dataclass
class DownloadProgress:
    """進度追蹤資料類別 / 與 ProgressBar 整合"""

    completed_segments: int = 0
    total_segments: int = 0
    current_bytes: int = 0
    speed_mbps: float = 0.0
    eta_seconds: float = 0.0


class MediaDownloader:
    """媒體下載器 - 支援多軌同時下載與進度顯示"""

    MB_IN_BYTES = 1024 * 1024

    def __init__(self, media_id: str, output_dir: str, video_duration: float) -> None:
        self.media_id: str = media_id
        self.base_dir: Path = Path(output_dir)
        self.video_duration: float = video_duration
        self.dl_obj: DownloadObjection = DownloadObjection()

        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock: asyncio.Lock = asyncio.Lock()
        self._thread_pool: Optional[ThreadPoolExecutor] = None

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=4)
        return self._thread_pool
    
    async def _ensure_session(self) -> None:
        """確保 aiohttp session 存在 使用 Lock 避免 race condition"""
        async with self._session_lock:
            if self._session is not None and not self._session.closed:
                return

            connector = aiohttp.TCPConnector(
                limit=CFG["VideoDownload"]["connector_limit"],
                limit_per_host=CFG["VideoDownload"]["connector_limit_per_host"],
                ttl_dns_cache=CFG["VideoDownload"]["connector_ttl_dns_cache"],
                use_dns_cache=CFG["VideoDownload"]["connector_use_dns_cache"],
                keepalive_timeout=CFG["VideoDownload"]["connector_keepalive_timeout"],
                enable_cleanup_closed=CFG["VideoDownload"]["connector_enable_cleanup_closed"],
                force_close=False,
                family=socket.AF_INET,
                resolver=aiohttp.AsyncResolver(),
            )

            timeout = ClientTimeout(
                total=CFG["VideoDownload"]["timeout_total"],
                connect=CFG["VideoDownload"]["timeout_connect"],
                sock_read=CFG["VideoDownload"]["timeout_sock_read"],
                sock_connect=CFG["VideoDownload"]["timeout_sock_connect"],
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "user-agent": USERAGENT,
                    "accept": "*/*",
                    "accept-encoding": "gzip, deflate, br",
                    "connection": "keep-alive",
                },
                cookie_jar=aiohttp.DummyCookieJar(),
                auto_decompress=True,
                read_bufsize=256 * 1024,
            )

    async def close(self) -> None:
        """關閉 session 與 thread pool 釋放所有資源"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._thread_pool is not None:
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None

    async def download_file(self, url: str, save_path: Path) -> bool:
        """下載單一檔案 失敗時使用指數退避重試"""
        save_path.parent.mkdir(parents=True, exist_ok=True)
        max_retries: int = int(CFG["VideoDownload"]["max_retries"])

        for attempt in range(max_retries):
            await self._ensure_session()
            assert self._session is not None

            try:
                return await self.attempt_download(url, save_path, attempt)

            except asyncio.CancelledError:
                await self._cancel_cleanup(url, save_path)
                return False

            except (TimeoutError, aiohttp.ClientError) as exc:
                logger.warning(f"Download attempt {attempt + 1} failed: {exc}")
                if attempt + 1 < max_retries:
                    await asyncio.sleep(2 ** (attempt + 1))
                else:
                    logger.error(f"Download failed after {max_retries} retries: {url}")
                    return False

            except Exception as exc:
                if str(exc) == "Connection closed.":
                    return False
                logger.error(f"Unexpected error during download: {exc}")

        return False

    async def attempt_download(self, url: str, save_path: Path, attempt: int) -> bool:
        """發出單次 GET 請求並串流寫入磁碟"""
        proxy: str = await _get_random_proxy() or ""

        async with self._session.get(url, proxy=proxy) as response:
            if response.status not in (200, 206):
                logger.warning(
                    f"Request failed with status {response.status}, "
                    f"retrying (attempt {attempt + 1})..."
                )
                await asyncio.sleep(2 ** (attempt + 1))
                return False

            await self.stream_to_disk(response, save_path)
            return True
    
    async def stream_to_disk(
        self,
        response: aiohttp.ClientResponse,
        save_path: Path,
    ) -> None:
        async with aiofiles.open(save_path, "wb") as fh:
            async for chunk in response.content.iter_chunked(64 * 1024):
                await fh.write(chunk)

    async def _cancel_cleanup(self, url: str, save_path: Path) -> None:
        progress_manager.remove_all_progress_bars()
        await self.close()
        await self.force_remove_file(save_path)
        logger.info(f"Download cancelled: {url}")
        
    async def force_remove_file(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
                logger.info(
                    f"{Color.fg('yellow_ochre')}Successfully removed "
                    f"{Color.fg('denim')}{path}{Color.reset()}"
                )
        except OSError as exc:
            logger.warning(f"Failed to remove file {path}: {exc}")

    def check_download_dir(self, folder_path: Path) -> bool:
        """檢查下載目錄是否存在"""
        if not os.path.exists(folder_path):
            paramstore._store["slice_path_fail"] = True
            logger.warning(f"{Color.fg('light_gray')}Fail to create directory{Color.reset()}: {folder_path}")
            return False
        return True

    def mada_track_dir_path(self, track_type: str, track: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack) -> Path:
        """生成軌道的目錄路徑"""
        if track_type == "subtitle":
            return self.base_dir / track_type / track.language
        else:
            return self.base_dir / track_type

    async def _merge_track(self, track_type: str, track: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack) -> bool:
        """合併軌道片段"""
        track_dir: Path = self.mada_track_dir_path(track_type, track)
        
        output_file: Path = self.base_dir / f"{track_type}.{container}"

        init_files: list[Path] = list(track_dir.glob(f"init_{track_type}_.*"))
        
        if not init_files:
            if paramstore.get("mpd_audio") is True and track_type == "audio":
                logger.warning(f"Could not find {track_type} initialization file")
                return False
            if paramstore.get("mpd_video") is True and track_type == "video":
                logger.warning(f"Could not find {track_type} initialization file")
                return False

        segments: list[Path] = sorted(
            [p for p in track_dir.glob("seg_*.*") if len(p.stem.split("_")) == 3 and p.stem.split("_")[2].isdigit()],
            key=lambda x: int(x.stem.split("_")[2]),
        )
        
        if not segments:
            if paramstore.get("mpd_audio") is True and track_type == "audio":
                logger.warning(f"No {track_type} fragment files found")
                return False
            if paramstore.get("mpd_video") is True and track_type == "video":
                logger.warning(f"No {track_type} fragment files found")
                return False

        if len(segments) >= 1 and track_type != "subtitle":
            result: bool = await MERGE.binary_merge(output_file, init_files, segments, track_type)
            logger.debug(f"{Color.fg('light_gray')}Merge {track_type} tracks: {len(segments)} segments{Color.reset()}")
            if result:
                self.dl_obj.audio = output_file if track_type == "audio" else self.dl_obj.audio
                self.dl_obj.video = output_file if track_type == "video" else self.dl_obj.video
            return result
        elif len(segments) >= 1 and track_type == "subtitle":
            subtitle_str: str = SubtitleProcessor(track, segments).process_subtitle(init_files)
            subtitle_path: Path = output_file.with_name(f"{track.language}{output_file.with_suffix('').suffix}.srt")
            result: bool = await MERGE.save_subtitle(track.language, subtitle_str, subtitle_path)
            if result:
                self.dl_obj.subtitle[track.language] = subtitle_path
            return result

    async def download_track_with_manager(
        self,
        track: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack,
        track_type: str,
        progress_manager: MultiTrackProgressManager,
    ) -> bool:
        """使用多軌管理器的下載方法"""
        
        track_dir: Path = self.mada_track_dir_path(track_type, track)

        try:
            track_dir.mkdirp()
        except FileNotFoundError as e:
            logger.info(f"{Color.bg('firebrick')}The folder name may contain spaces, illegal characters, and cannot meet the specifications.{Color.reset()}")
            paramstore._store["slice_path_fail"] = True
            logger.error(e)
            return False

        if not self.check_download_dir(track_dir):
            return False
        
        track_id: str = track.id
        init_path: Path = track_dir / f"init_{track_type}_{Path(track.init_url).suffix}"
        if track.init_url.rstrip("/").split("/")[-1].split(".")[0] == "init" and track.mime_type in ("video/mp4", "audio/mp4", "application/mp4"):
            if not await self.download_file(track.init_url, init_path):
                logger.error(f"{track_type} Initialization file download failed")
                return False

        logger.info(f"{Color.fg('light_gray')}Start downloading{Color.reset()} {Color.bg('cyan')}{track_type}{Color.reset()} track: {Color.fg('cyan')}{track_id}{Color.reset()}")

        if track.segment_urls:
            return await self.task_and_dl_with_manager(track, track_dir, track_type, progress_manager)

        return True

    async def task_and_dl_with_manager(
        self,
        track: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack,
        track_dir: Path,
        track_type: str,
        progress_manager: MultiTrackProgressManager,
    ) -> bool:
        """使用多軌管理器的批次下載方法"""
        total: int = len(track.segment_urls)
        success_count: int = 0
        semaphore: asyncio.Semaphore = asyncio.Semaphore(CFG["VideoDownload"]["semaphore"])

        progress: DownloadProgress = DownloadProgress(total_segments=total, completed_segments=0, current_bytes=0)

        progress_bar = progress_manager.create_progress_bar(
            track_type, total, f"{int(self.video_duration / 60)} min {int(self.video_duration % 60)} sec")

        progress_lock: asyncio.Lock = asyncio.Lock()
            
        async def bounded_download(i: int, url: str):
            async with semaphore:
                seg_path: Path = track_dir / f"seg_{track_type}_{i}{Path(url).suffix}"
                susscess_bool: bool = await self.download_file(url, seg_path)
                async with progress_lock:
                    progress.completed_segments += 1
                return susscess_bool

        tasks: asyncio.Task = [bounded_download(i, url) for i, url in enumerate(track.segment_urls)]

        try:
            for coro in asyncio.as_completed(tasks):
                susscess_bool: bool = await coro
                success_count += int(susscess_bool)
                progress_bar.update(download_progress=progress)
        except asyncio.CancelledError:
            progress_manager.remove_all_progress_bars()
            if self._session:
                await self._session.close()
            logger.info("Download cancelled")
            return False
        
        return success_count == total

    async def download_content(self, mpd_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack) -> tuple[bool, DownloadObjection]:
        """下載所有軌道內容"""
        try:
            track_tasks: list[tuple[str, MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack]] = []
            match paramstore.get("subs_only"):
                case True:
                    logger.info(f"{Color.fg('tomato')}【Subs only mode】{Color.reset()}")
                    if mpd_content.sub_track:
                        for hlssubtrack in mpd_content.sub_track:
                           track_tasks.append(("subtitle", hlssubtrack))
                case _:
                    if mpd_content.audio_track:
                        track_tasks.append(("audio", mpd_content.audio_track))
                    if mpd_content.video_track:
                        track_tasks.append(("video", mpd_content.video_track))
                    if mpd_content.sub_track:
                        for hlssubtrack in mpd_content.sub_track:
                            track_tasks.append(("subtitle", hlssubtrack))
                
            # 啟動進度條
            if len(track_tasks) > 0:
                progress_manager.start()
                
            tasks: list[asyncio.Task] = []
            for track_type, track in track_tasks:
                task: asyncio.Task = self.download_track_with_manager(track, track_type, progress_manager)
                tasks.append(task)

            if tasks:
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    await self.close()
                    sys.exit(1)
                    
            # 關閉進度條
            if len(track_tasks) > 0:
                progress_manager.stop()

            # 合併軌道
            if paramstore.get("skip_merge") is not True:
                merge_results: list[bool] = []
                if mpd_content.video_track:
                    merge_results.append(await self._merge_track("video", mpd_content.video_track))
                if mpd_content.audio_track:
                    merge_results.append(await self._merge_track("audio", mpd_content.audio_track))
                if mpd_content.sub_track:
                    for sub in mpd_content.sub_track:
                        merge_results.append(await self._merge_track("subtitle", sub))
                if all(merge_results):
                    self.dl_obj.task_info = track_tasks
                return all(merge_results), self.dl_obj
            else:
                logger.info(f"{Color.fg('light_gray')}Skip merge because --skip-merge is {Color.fg('cyan')}True{Color.reset()}")
                return False, self.dl_obj
        finally:
            await self.close()

    async def force_remove_dir(self, path: Path) -> bool:
        if path.exists():
            path.unlink()
            # shutil.rmtree(path, ignore_errors=False)
            logger.info(f"{Color.fg('yellow_ochre')}Successfully removed {Color.fg('denim')}{path}{Color.reset()}")


class Start_Download_Queue:
    def __init__(
        self,
        decryption_key: list[str],
        public_info: PublicInfo,
        playback_info: PlaybackInfo,
        raw_mpd: ClientResponse,
        raw_hls: str,
        input_community_name: str,
    ) -> None:
        self.decryption_key: list[str] = decryption_key
        self.public_info: PublicInfo = public_info
        self.playback_info: PlaybackInfo = playback_info
        self.raw_mpd: ClientResponse = raw_mpd
        self.raw_hls: str = raw_hls
        self.input_community_name: str = input_community_name
        self._community_name: str = None
        self._custom_community_name: str = None
        self.dl_obj: DownloadObjection = None

    @cached_property
    def vv(self):
        return Video_folder(self.public_info, self.input_community_name, self.dl_obj, self.decryption_key)

    @cached_property
    async def community_name(self) -> str:
        return await self.vv.get_community_name()

    @cached_property
    async def custom_community_name(self) -> str:
        custom_name, _ = await self.vv.get_custom_community_name()
        return custom_name

    async def get_output_dir(self) -> tuple[Path, str, str]:
        community_name, custom_community_name = await self.vv.get_custom_community_name()
        output_dir: Path = await self.vv.video_folder_handle(community_name, custom_community_name)
        return output_dir, community_name, custom_community_name

    async def task_of_info(
        self,
        output_dir: Path,
        custom_community_name: str,
        community_name: str,
        playlist_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack,
    ) -> None:
        savejsondata = save_json_data(
            output_dir,
            custom_community_name,
            community_name,
            self.public_info,
            self.playback_info,
        )
        await asyncio.gather(
            savejsondata.mpd_to_folder(self.raw_mpd),
            savejsondata.hls_to_folder(self.raw_hls),
            savejsondata.json_data_to_folder(),
            savejsondata.play_list_to_folder(playlist_content),
            savejsondata.dl_thumbnail(),
        )

    async def start_request_download(
        self,
        output_dir: Path,
        playlist_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack,
        video_duration: float,
    ) -> tuple[bool, DownloadObjection]:
        self.downloader: MediaDownloader = MediaDownloader(self.public_info.media_id, output_dir, video_duration)
        success, dl_obj = await self.downloader.download_content(playlist_content)
        return success, dl_obj

    async def start_rename(
        self,
        custom_community_name: str,
        community_name: str,
        success: bool,
        output_dir: Path,
    ) -> tuple[str, bool]:
        s: SUCCESS = SUCCESS(
            self.dl_obj,
            output_dir,
            self.public_info,
            self.playback_info,
            custom_community_name,
            community_name,
            self.decryption_key,
        )
        video_file_name, mux_bool_status = await s.when_success(success)
        return video_file_name, mux_bool_status

    async def start_download_queue(self, playlist_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack, video_duration: float) -> None:
        """協調資料夾創建、資訊儲存、下載和後續處理的整個流程"""
        if playlist_content is None:
            logger.error("Failed to parse Playlist.")
            return
        
        output_dir, custom_community_name, community_name = await self.get_output_dir()
        
        if output_dir is not None and output_dir.exists():
            await self.task_of_info(output_dir, custom_community_name, community_name, playlist_content)
            success, dl_obj = await self.start_request_download(output_dir, playlist_content, video_duration)
            self.dl_obj: DownloadObjection = dl_obj 
            # 處理成功後的混流 重命名和清理
            video_file_name, mux_bool_status = await self.start_rename(custom_community_name, community_name, success, output_dir)
            await self.vv.re_name_folder(video_file_name, mux_bool_status)
        else:
            logger.error("Failed to create output directory.")
            raise ValueError("No output directory")

    async def run_dl(self) -> Never:
        start_time = None
        end_time = None

        v_resolution_choice, a_resolution_choice, video_codec = ConfigLoader._check_hls_dash(CFG)

        if paramstore.get("start_time") is not None:
            start_time = self.video_start2end_time(paramstore.get("start_time"))
        if paramstore.get("end_time") is not None:
            end_time = self.video_start2end_time(paramstore.get("end_time"))
            
        hls_content: HLSContent = await HLS_Paser().parse_playlist(self.raw_hls, self.playback_info.hls_playback_url)
        mpd_parser: MPDParser = MPDParser(self.raw_mpd, self.playback_info.dash_playback_url)
        mpd_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack = await mpd_parser.parse_all_tracks()

        if self.playback_info.drm_info is None:
            selector: PlaylistSelector = PlaylistSelector(hls_content, mpd_content, "all", start_time, end_time)
        else:
            selector: PlaylistSelector = PlaylistSelector(hls_content, mpd_content, "mpd", start_time, end_time)
            
        match paramstore.get("get_v_list"):
            case True:
                PlaylistSelector(hls_content, mpd_content, "all", start_time, end_time).print_parsed_content()
            case _:
                if paramstore.get("subs_only") is True:
                    playlist_content: HLSSubTrack | SubtitleTrack = await selector.select_tracks("None", "None", "H264", paramstore.get("slang"))
                else:
                    playlist_content: MediaTrack | HLSVariant | HLSSubTrack | SubtitleTrack = await selector.select_tracks(
                        v_resolution_choice, a_resolution_choice, video_codec, paramstore.get("slang"))

                if paramstore.get("nodl") is True:
                    logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()}")
                else:
                    await self.start_download_queue(playlist_content, self.playback_info.duration)

    def video_start2end_time(self, time: float | int | str) -> float:
        sort_time = video_start2end_time(time)
        return sort_time
