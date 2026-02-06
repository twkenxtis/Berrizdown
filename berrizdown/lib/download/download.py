import asyncio
import os
import socket
import random
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cached_property
from io import BytesIO
from typing import Any

import aiohttp
from aiohttp import ClientTimeout, ClientResponse

from berrizdown.lib.__init__ import use_proxy
from berrizdown.lib.__init__ import container
from berrizdown.lib.Proxy import Proxy
from berrizdown.lib.load_yaml_config import CFG, ConfigLoader
from berrizdown.lib.mux.merge import MERGE
from berrizdown.lib.mux.parse_hls import HLS_Paser, HLSContent
from berrizdown.lib.mux.parse_mpd import MediaTrack, MPDContent, MPDParser
from berrizdown.lib.mux.playlist_selector import PlaylistSelector
from berrizdown.lib.path import Path
from berrizdown.lib.processbar.processbar import MultiTrackProgressManager
from berrizdown.lib.rename.rename import SUCCESS
from berrizdown.lib.save_json_data import save_json_data
from berrizdown.lib.subdl import SaveSub
from berrizdown.lib.video_folder import Video_folder
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.PlaybackInfo import PlaybackInfo
from berrizdown.static.PublicInfo import PublicInfo
from berrizdown.unit.__init__ import USERAGENT, FilenameSanitizer
from berrizdown.unit.date.date import video_start2end_time
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
class DownloadProgress:
    """進度追蹤資料類別 / 與 ProgressBar 整合"""

    completed_segments: int = 0
    total_segments: int = 0
    current_bytes: int = 0
    total_bytes: int = 0
    speed_mbps: float = 0.0
    eta_seconds: float = 0.0
    # 可選的媒體資訊
    fps: float = 0.0
    codec: str = ""
    ping_ms: float = 0.0
    total_size_mb: float = 0.0
    duration_seconds: float = 0.0


class MediaDownloader:
    """媒體下載器 - 支援多軌同時下載與進度顯示"""

    MB_IN_BYTES = 1024 * 1024

    def __init__(self, media_id: str, output_dir: str, video_duration: float) -> None:
        self.media_id: str = media_id
        self.base_dir: Path = Path(output_dir)
        self.session: aiohttp.ClientSession | None = None
        self.video_duration: float = video_duration
        self._thread_pool: ThreadPoolExecutor | None = None

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=4)
        return self._thread_pool

    def _get_file_extension(self, mime_type: str) -> str:
        """根據 MIME 類型確定檔案副檔名"""
        mime_type = mime_type.lower()

        # Manifest types
        if "application/dash+xml" in mime_type:
            return ".mpd"
        if "application/x-mpegurl" in mime_type or "application/vnd.apple.mpegurl" in mime_type:
            return ".m3u8"

        # MP4 family
        if "video/mp4" in mime_type:
            return ".mp4"
        if "audio/mp4" in mime_type:
            return ".m4a"

        # WebM family
        if "video/webm" in mime_type:
            return ".webm"
        if "audio/webm" in mime_type:
            return ".weba"

        # MPEG transport stream
        if "video/mp2t" in mime_type:
            return ".ts"

        # Raw segments
        if "application/octet-stream" in mime_type:
            return ".m4s"

        # Subtitles
        if "text/vtt" in mime_type:
            return ".vtt"
        if "text/ttml" in mime_type or "application/ttml+xml" in mime_type:
            return ".ttml"
        if "application/x-subrip" in mime_type:
            return ".srt"

        # Audio codecs
        if "audio/aac" in mime_type:
            return ".aac"
        if "audio/ogg" in mime_type:
            return ".ogg"
        if "audio/opus" in mime_type:
            return ".opus"
        if "audio/flac" in mime_type:
            return ".flac"
        if "audio/wav" in mime_type or "audio/x-wav" in mime_type:
            return ".wav"
        if "audio/mpeg" in mime_type:
            return ".mp3"

        # Video codecs
        if "video/h264" in mime_type or "video/avc" in mime_type:
            return ".h264"
        if "video/h265" in mime_type or "video/hevc" in mime_type:
            return ".h265"
        if "video/av1" in mime_type:
            return ".av1"
        if "video/x-matroska" in mime_type:
            return ".mkv"

        # Fallback
        return ".bin"

    async def _ensure_session(self) -> None:
        """確保 session 存在"""
        if self.session is None or self.session.closed:
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

            self.session = aiohttp.ClientSession(
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

    async def _preflight_requests(self, urls: list[str], batch_size: int = 16) -> dict[str, dict[str, any]]:
        """批次預先處理 HEAD 請求，獲取 Range 和檔案資訊"""
        await self._ensure_session()
        results = {}

        async def fetch_head(url: str) -> tuple[str, dict]:
            try:
                async with self.session.head(
                    url,
                    allow_redirects=True,
                    timeout=ClientTimeout(total=10),
                    proxy=await _get_random_proxy() or "",
                ) as resp:
                    return url, {
                        "size": int(resp.headers.get("Content-Length", 0)),
                        "accept_ranges": resp.headers.get("Accept-Ranges") == "bytes",
                        "etag": resp.headers.get("ETag", ""),
                        "content_type": resp.headers.get("Content-Type", ""),
                        "last_modified": resp.headers.get("Last-Modified", ""),
                    }
            except Exception as e:
                logger.debug(f"HEAD request failed for {url}: {e}")
                return url, {
                    "size": 0,
                    "accept_ranges": False,
                    "etag": "",
                    "content_type": "",
                    "last_modified": "",
                }

        semaphore = asyncio.Semaphore(batch_size)

        async def bounded_fetch(url):
            async with semaphore:
                return await fetch_head(url)

        tasks = [bounded_fetch(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for response in responses:
            if isinstance(response, Exception):
                continue
            url, info = response
            results[url] = info

        return results

    async def _download_file_optimized(
        self,
        url: str,
        save_path: Path,
        max_retries: int = CFG["VideoDownload"]["max_retries"],
        progress_callback: Callable[[int], None] | None = None,
        file_info: dict | None = None,
    ) -> bool:
        """優化的下載方法：全部使用 BytesIO"""
        retries = 0
        save_path.parent.mkdirp()

        while retries <= max_retries:
            await self._ensure_session()
            try:
                assert self.session is not None

                async with self.session.get(
                    url,
                    proxy = await _get_random_proxy() or "",
                    ) as response:
                    logger.debug(f"Downloading {Color.fg('cyan')}{url}{Color.reset()} to {save_path}")

                    if response.status not in (200, 206):
                        logger.warning(f"Request failed with status {response.status}, retrying...")
                        retries += 1
                        await asyncio.sleep(2**retries)
                        continue

                    buffer = BytesIO()
                    try:
                        while True:
                            chunk = await response.content.readany()
                            if not chunk:
                                break
                            buffer.write(chunk)
                            if progress_callback:
                                progress_callback(len(chunk))

                        # 一次性寫入磁碟
                        loop = asyncio.get_event_loop()
                        buffer_data = buffer.getvalue()
                        await loop.run_in_executor(
                            self.thread_pool,
                            lambda: save_path.write_bytes(buffer_data),
                        )
                    finally:
                        buffer.close()

                    return True

            except asyncio.CancelledError:
                progress_manager.remove_all_progress_bars()
                if self.session:
                    await self.session.close()
                await self.force_remove_dir(save_path)
                # await self.force_remove_dir(save_path.parents[2])
                logger.info(f"Download cancelled: {url}")
                return False
            except (TimeoutError, aiohttp.ClientError) as e:
                logger.warning(f"Download attempt {retries + 1} failed: {str(e)}")
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(2**retries)
                else:
                    logger.error(f"Download failed after {max_retries} retries: {url}")
                    return False
            except Exception as e:
                if str(e) == "Connection closed.":
                    return False
                logger.error(f"Unexpected error during download: {e}")
                retries += 1
        return False

    async def _download_file(
        self,
        url: str,
        save_path: Path,
        max_retries: int = 3,
        progress_callback: Callable[[int], Any] | None = None,
    ) -> bool:
        """下載單個檔案的入口方法"""
        return await self._download_file_optimized(
            url=url,
            save_path=save_path,
            max_retries=max_retries,
            progress_callback=progress_callback,
        )

    def check_download_dir(self, folder_path: Path) -> bool:
        """檢查下載目錄是否存在"""
        if not os.path.exists(folder_path):
            paramstore._store["slice_path_fail"] = True
            logger.warning(f"{Color.fg('light_gray')}Fail to create directory{Color.reset()}: {folder_path}")
            return False
        return True

    def duration(self) -> str:
        """格式化影片時長"""
        minutes = int(self.video_duration / 60)
        seconds = int(self.video_duration % 60)
        return f"{minutes} min {seconds} sec"

    async def _merge_track(self, track_type: str) -> bool:
        """合併軌道片段"""
        track_dir: Path = self.base_dir / track_type
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

        if len(segments) >= 1:
            result: bool = await MERGE.binary_merge(output_file, init_files, segments, track_type)
            logger.debug(f"{Color.fg('light_gray')}Merge {track_type} tracks: {len(segments)} segments{Color.reset()}")
            return result

    async def download_track_with_manager(
        self,
        track: MediaTrack,
        track_type: str,
        progress_manager: MultiTrackProgressManager,
    ) -> bool:
        """使用多軌管理器的下載方法"""
        track_dir: Path = self.base_dir / track_type

        try:
            track_dir.mkdirp()
        except FileNotFoundError as e:
            logger.info(f"{Color.bg('firebrick')}The folder name may contain spaces, illegal characters, and cannot meet the specifications.{Color.reset()}")
            paramstore._store["slice_path_fail"] = True
            logger.error(e)
            return False

        if not self.check_download_dir(track_dir):
            return False

        slice_parameters = track.segment_urls
        file_ext = self._get_file_extension(track.mime_type)
        track_id = track.id

        init_path: Path = track_dir / f"init_{track_type}_{file_ext}"

        if track.init_url.rstrip("/").split("/")[-1].split(".")[0] == "init" and track.mime_type in ("video/mp4", "audio/mp4"):
            if not await self._download_file(track.init_url, init_path):
                logger.error(f"{track_type} Initialization file download failed")
                return False

        logger.info(f"{Color.fg('light_gray')}Start downloading{Color.reset()} {Color.bg('cyan')}{track_type}{Color.reset()} track: {Color.fg('cyan')}{track_id}{Color.reset()}")

        if slice_parameters:
            return await self.task_and_dl_with_manager(slice_parameters, track_dir, file_ext, track_type, progress_manager)

        return True

    async def task_and_dl_with_manager(
        self,
        slice_parameters: list[str],
        track_dir: Path,
        file_ext: str,
        track_type: str,
        progress_manager: MultiTrackProgressManager,
    ) -> bool:
        """使用多軌管理器的批次下載方法"""
        total = len(slice_parameters)
        success_count = 0
        semaphore = asyncio.Semaphore(CFG["VideoDownload"]["semaphore"])

        progress = DownloadProgress(total_segments=total, completed_segments=0, current_bytes=0, total_bytes=0)

        # 獲取所有檔案的 Range 和大小資訊
        file_info_map = await self._preflight_requests(slice_parameters)

        progress.total_bytes = sum(info.get("size", 0) for info in file_info_map.values())
        progress.total_size_mb = progress.total_bytes / self.MB_IN_BYTES

        # 創建此軌道的進度條
        progress_bar = progress_manager.create_progress_bar(track_type, total, self.duration())

        progress_lock = asyncio.Lock()
        start_time = time.time()

        async def progress_callback(bytes_downloaded: int):
            async with progress_lock:
                progress.current_bytes += bytes_downloaded
                elapsed = time.time() - start_time
                if elapsed > 0:
                    progress.speed_mbps = (progress.current_bytes / self.MB_IN_BYTES) / elapsed
                    remaining_bytes = progress.total_bytes - progress.current_bytes
                    if progress.speed_mbps > 0:
                        progress.eta_seconds = remaining_bytes / (progress.speed_mbps * self.MB_IN_BYTES)

        async def bounded_download(i: int, url: str):
            async with semaphore:
                seg_path = track_dir / f"seg_{track_type}_{i}{file_ext}"
                file_info = file_info_map.get(url, {})

                result = await self._download_file_optimized(
                    url,
                    seg_path,
                    progress_callback=lambda b: asyncio.create_task(progress_callback(b)),
                    file_info=file_info,
                )

                async with progress_lock:
                    progress.completed_segments += 1
                return result

        tasks = [bounded_download(i, url) for i, url in enumerate(slice_parameters)]

        try:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                success_count += int(result)
                progress_bar.update(download_progress=progress)
        except asyncio.CancelledError:
            progress_manager.remove_all_progress_bars()
            if self.session:
                await self.session.close()
            logger.info("Download cancelled")
            return False
        print(
            f"{Color.fg('pink')}{track_type} {Color.fg('light_gray')}(Avg: {progress.speed_mbps:.2f} MB/s)"
            f" finished in {Color.fg('blush')}{time.time() - start_time:.2f} {Color.fg('light_gray')}seconds{Color.reset()}"
            f"{Color.fg('flamingo_pink')} {total}/{Color.fg('magenta_pink')}{success_count} "
            f"{Color.fg('light_gray')}segments successfully downloaded{Color.reset()}"
        )
        return success_count == total

    async def download_content(self, mpd_content: MPDContent | HLS_Paser) -> bool:
        """下載所有軌道內容"""
        try:
            track_tasks = []
            if mpd_content.audio_track:
                track_tasks.append(("audio", mpd_content.audio_track))
            if mpd_content.video_track:
                track_tasks.append(("video", mpd_content.video_track))

            # 啟動進度條
            if len(track_tasks) > 0:
                progress_manager.start()

            tasks = []
            for track_type, track in track_tasks:
                task = self.download_track_with_manager(track, track_type, progress_manager)
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
                merge_results = []
                if mpd_content.video_track:
                    merge_results.append(await self._merge_track("video"))
                if mpd_content.audio_track:
                    merge_results.append(await self._merge_track("audio"))
                # if mpd_content.video_track and mpd_content.audio_track:
                return all(merge_results)
            else:
                logger.info(f"{Color.fg('light_gray')}Skip merge because --skip-merge is {Color.fg('cyan')}True{Color.reset()}")
                return False
        finally:
            await self.close()

    async def force_remove_dir(self, path: Path) -> bool:
        if path.exists():
            path.unlink()
            # shutil.rmtree(path, ignore_errors=False)
            logger.info(f"{Color.fg('yellow_ochre')}Successfully removed {Color.fg('denim')}{path}{Color.reset()}")

    async def close(self) -> None:
        """關閉 session 和線程池"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self._thread_pool is not None:
            self._thread_pool.shutdown(wait=True)


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
        self._community_name = None
        self._custom_community_name = None

    @cached_property
    def vv(self):
        return Video_folder(self.public_info, self.input_community_name)

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
        playlist_content: MPDContent | HLSContent,
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
        output_dir,
        playlist_content: MPDContent | HLSContent,
        video_duration: float,
    ) -> bool:
        self.downloader: MediaDownloader = MediaDownloader(self.public_info.media_id, output_dir, video_duration)
        success: bool = await self.downloader.download_content(playlist_content)
        return success

    async def start_rename(
        self,
        custom_community_name: str,
        community_name: str,
        success: bool,
        output_dir: Path,
    ) -> tuple[str, bool]:
        s: SUCCESS = SUCCESS(
            output_dir,
            self.public_info,
            self.playback_info,
            custom_community_name,
            community_name,
        )
        try:
            video_file_name, mux_bool_status = await s.when_success(success, self.decryption_key)
        except TypeError:
            logger.warning("Cancelled")
            sys.exit(1)
        return video_file_name, mux_bool_status

    async def start_download_queue(self, playlist_content: MPDContent | HLSContent, video_duration: float) -> None:
        """協調資料夾創建、資訊儲存、下載和後續處理的整個流程"""
        if playlist_content is None:
            logger.error("Failed to parse Playlist.")
            return
        
        output_dir, custom_community_name, community_name = await self.get_output_dir()
        
        savejsondata = save_json_data(
            output_dir,
            custom_community_name,
            community_name,
            self.public_info,
            self.playback_info,
        )
        savesub: SaveSub = SaveSub(output_dir, self.raw_hls, savejsondata.sub_meta())
        
        if output_dir is not None and os.path.exists(output_dir) and not paramstore.get("subs_only") is True:
            if not paramstore.get("no_subs") is True:
                await savesub.start()
            await self.task_of_info(output_dir, custom_community_name, community_name, playlist_content)
            success = await self.start_request_download(output_dir, playlist_content, video_duration)
            # 處理成功後的混流、重命名和清理
            video_file_name, mux_bool_status = await self.start_rename(custom_community_name, community_name, success, output_dir)
            await self.vv.re_name_folder(video_file_name, mux_bool_status)
        elif paramstore.get("subs_only") is True:
            logger.info(f"{Color.fg('tomato')}【Subs only mode】{Color.reset()}")
            await savesub.start()
        else:
            logger.error("Failed to create output directory.")
            raise ValueError

    async def run_dl(self) -> None:
        start_time = None
        end_time = None

        v_resolution_choice, a_resolution_choice, video_codec = ConfigLoader._check_hls_dash(CFG)

        if paramstore.get("start_time") is not None:
            start_time = self.video_start2end_time(paramstore.get("start_time"))
        if paramstore.get("end_time") is not None:
            end_time = self.video_start2end_time(paramstore.get("end_time"))
        hls_parser = HLS_Paser()
        hls_content = await hls_parser.parse_playlist(self.raw_hls, self.playback_info.hls_playback_url)
        mpd_parser = MPDParser(self.raw_mpd, self.playback_info.dash_playback_url)
        mpd_content = await mpd_parser.parse_all_tracks()

        if self.playback_info.drm_info is None:
            selector = PlaylistSelector(hls_content, mpd_content, "all", start_time, end_time)
        else:
            selector = PlaylistSelector(hls_content, mpd_content, "mpd", start_time, end_time)
            
        match paramstore.get("get_v_list"):
            case True:
                PlaylistSelector(hls_content, mpd_content, "all", start_time, end_time).print_parsed_content()
            case _:
                if paramstore.get("subs_only") is True:
                    playlist_content = await selector.select_tracks("None", "None", "H264")
                else:
                    playlist_content = await selector.select_tracks(v_resolution_choice, a_resolution_choice, video_codec)

                if paramstore.get("nodl") is True:
                    logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()}")
                    return False
                else:
                    await self.start_download_queue(playlist_content, self.playback_info.duration)

    def video_start2end_time(self, time: float | int | str) -> float:
        sort_time = video_start2end_time(time)
        return sort_time
