import asyncio
import ctypes
import os
import subprocess
from pathlib import Path
from typing import Any


from berrizdown.lib.__init__ import container
from berrizdown.lib.load_yaml_config import CFG, ConfigLoader
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.route import Route
from berrizdown.unit.handle.handle_log import setup_logging


logger = setup_logging("mux", "lavender")


def get_short_path_name(long_path: Path) -> str:
    """將 Windows 長路徑轉換為短路徑（8.3 格式），避免中文路徑問題"""
    long_path_str = str(long_path.resolve())
    
    # 取得短路徑所需的緩衝區大小
    buffer_size = ctypes.windll.kernel32.GetShortPathNameW(long_path_str, None, 0)
    
    if buffer_size == 0:
        # 如果失敗，回傳原路徑
        logger.warning(f"Cannot get short path for: {long_path_str}, using original path")
        return long_path_str
    
    # 建立緩衝區並取得短路徑
    buffer = ctypes.create_unicode_buffer(buffer_size)
    ctypes.windll.kernel32.GetShortPathNameW(long_path_str, buffer, buffer_size)
    
    return buffer.value


class FFmpegMuxer:
    base_dir: Path
    decryption_key: list[Any] | None

    def __init__(self, base_dir: Path, isdrm: bool, subs_successful: list[tuple[str, str, Path]]|list, decryption_key: list[str] | None = None):
        self.base_dir: Path = base_dir
        self.decryption_key: list[str] | None = decryption_key
        self.key: str = None
        self.input_path: Path = None
        self.output_path: Path = None
        self.isdrm: bool = isdrm
        self.subs_successful: list[tuple[str, str, Path]]|list = subs_successful

    async def _prepare_track(self, track_type: str) -> Path | None:
        """Handle decryption if needed and return final file path"""
        input_file: Path = self.base_dir / f"{track_type}.{container}"
        self.input_path: Path = input_file
        if not input_file.exists():
            return None

        if self.decryption_key:
            decryption_key: str = await self.process_decryption_key()
            decrypted_file: Path = self.base_dir / f"{track_type}_decrypted.{container}"

            self.key = decryption_key
            self.output_path: Path = decrypted_file

            logger.info(
                f"{Color.fg('blue')}Detected{Color.reset()} {Color.fg('cyan')}{track_type} {Color.reset()}{Color.fg('blue')}"
                f"{Color.reset()}{Color.fg('blue')}decrypting...{Color.reset()}"
                f"{Color.fg('cyan')} {self.key}{Color.reset()}"
            )
            if await self.decrypt():
                return decrypted_file
            return None
        # No encryption, use original file
        return input_file

    async def process_decryption_key(self) -> str:
        if type(self.decryption_key) is list:
            key: str = " ".join([str(sublist).replace("[", "").replace("]", "") for sublist in self.decryption_key])
            return key
        elif type(self.decryption_key) is str:
            return self.decryption_key
        return ""

    async def decrypt(self) -> bool:
        try:
            decryptionengine = CFG["Container"]["decryption-engine"]
            decryptionengine = decryptionengine.upper()
        except AttributeError:
            ConfigLoader.print_warning("decryptionengine", decryptionengine, "shaka-packager")
            # decryptionengine = "MP4DECRYPT"
            decryptionengine = "SHAKA_PACKAGER"

        match decryptionengine:
            case "MP4DECRYPT":
                logger.info("decrypt by mp4decrypt")
                return await self._decrypt_file_mp4decrypt()
            case "SHAKA_PACKAGER":
                logger.info("decrypt by shaka-packager")
                return await self._decrypt_file_packager()
            case _:
                ConfigLoader.print_warning("decryptionengine", decryptionengine, "shaka-packager")
                return await self._decrypt_file_packager()

    async def _decrypt_file_mp4decrypt(self) -> bool:
        mp4decrypt_path: Path = Route().mp4decrypt_path

        if not mp4decrypt_path.exists():
            logger.error(f"mp4decrypt.exe not found at: {mp4decrypt_path}")
            return False

        try:
            # 轉換為短路徑
            mp4decrypt_short: str = get_short_path_name(mp4decrypt_path)
            input_short: str = get_short_path_name(self.input_path)
            output_short: str = get_short_path_name(self.output_path.parent) + "\\" + self.output_path.name
            
            # 分割 key 字串並為每個 key 添加 --key 參數
            key_parts: list[str] = self.key.split()
            key_args: list[str] = []
            for k in key_parts:
                key_args.extend(["--key", k])

            # 建立完整的命令
            command: list[str] = [mp4decrypt_short] + key_args + [input_short, output_short]

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Decryption failed for {self.input_path}: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error decrypting {self.input_path}: {str(e)}")
            return False

    async def _decrypt_file_packager(self) -> bool:
        packager_path: Path = Route().packager_path
        packager_output_path: Path = Path(self.output_path).with_suffix(".m4v")

        if not packager_path.exists():
            if paramstore.get("packager_path_ok") is True:
                packager_path_str = "packager"
            else:
                logger.error(f"shaka-packager.exe not found at: {packager_path}")
                return False
        else:
            # 轉換 packager 路徑為短路徑
            packager_path_str: str = get_short_path_name(packager_path)

        # 轉換輸入輸出路徑為短路徑
        input_short: str = get_short_path_name(self.input_path)
        
        # 輸出路徑需要先確保父目錄存在
        packager_output_path.parent.mkdir(parents=True, exist_ok=True)
        output_short: str = get_short_path_name(packager_output_path.parent) + "\\" + packager_output_path.name

        # 分割 key 字串並為每個 key 添加 --keys 參數
        key_lines: list[str] = self.key.strip().splitlines()
        key_args: list[str] = []

        for k in key_lines:
            try:
                kid, value = k.strip().split(":")
                key_args.extend(["--keys", f"key_id={kid}:key={value}"])
            except ValueError:
                logger.error(f"Invalid key format: {k}")
                return False

        # 建立完整的命令
        command: list[str] = [
            packager_path_str,
            f"input={input_short},stream_selector=0,output={output_short}",
            "--enable_raw_key_decryption",
        ] + key_args

        try:
            logger.debug(f"Packager command: {' '.join(command)}")
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            logger.debug(f"Packager output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Packager failed: {e.stderr}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error running packager: {e}")
            return False
        
        await asyncio.sleep(1.255)
        
        # 成功後.m4v 改回指定副檔名
        final_output_path = packager_output_path.with_suffix(f".{container}")
        packager_output_path.rename(final_output_path)
        return True

    async def mux_main(self, tempfile_path: Path) -> bool:
        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()}")
            return True
        elif paramstore.get("skip_merge") is True:
            logger.info(f"{Color.fg('light_gray')}Skip muxing{Color.reset()}")
            return False
        # Prepare video and audio tracks
        video_file: Path | None
        audio_file: Path | None
        try:
            video_file, audio_file = await asyncio.gather(
                self._prepare_track("video"),
                self._prepare_track("audio"),
            )
        except asyncio.CancelledError:
            logger.warning("Mux cancelled got cancelled signal")
            return False
        if self.decryption_key is None and self.isdrm is True:
            paramstore._store["no_key_drm"] = True
            logger.error("this is DRM Content but without decryption key, auto skip mux.")
            return False
        if paramstore.get("skip_mux") is True:
            return False
        elif paramstore.get("slice_path_fail") is True:
            logger.warning("No slice download skip mux.")
            return False
        elif paramstore.get("video_dl_cancelled") is True:
            return True
        elif video_file is None or audio_file is None:
            if video_file is not None:
                if os.path.exists(video_file):
                    os.rename(video_file, tempfile_path)
                    paramstore._store["no_video_audio"] = True
                    return True
            if audio_file is not None:
                if os.path.exists(audio_file):
                    paramstore._store["no_video_audio"] = True
                    os.rename(audio_file, tempfile_path)
                    return True
            return False

        # Standard FFmpeg command without modification
        temp_file_path: Path = self.base_dir / tempfile_path.name

        video_file_str: str = str(video_file) if video_file else ""
        audio_file_str: str | None = str(audio_file) if audio_file else None
        if paramstore.get("skip_mux") is True or paramstore.get("nodl") is True:
            return True
        else:
            return await self.choese_mux_tool(video_file_str, audio_file_str, temp_file_path)

    async def choese_mux_tool(self, video_file_str: str, audio_file_str: str, temp_file_path: Path):
        try:
            mux_tool = CFG["Container"]["mux"]
            mux_tool = mux_tool.upper()
        except AttributeError:
            ConfigLoader.print_warning("MUX", mux_tool, "ffmpeg")
            mux_tool = "FFMPEG"

        match mux_tool:
            case "FFMPEG":
                FFMPEG_path: Path = Route().ffmpeg
                if not FFMPEG_path.exists():
                    if paramstore.get("ffmpeg_path_ok") is True:
                        FFMPEG_path_str: str = "ffmpeg"
                    else:
                        logger.error(f"ffmpeg.exe not found at: {FFMPEG_path}")
                        return False
                else:
                    FFMPEG_path_str: str = get_short_path_name(FFMPEG_path)
                    
                cmd: list[str] = await self.build_ffmpeg_command(video_file_str, audio_file_str, temp_file_path, FFMPEG_path_str)

                try:
                    logger.info(f"{Color.fg('firebrick')}Start using FFmpeg to mux video and audio...{Color.reset()}")
                    result: subprocess.CompletedProcess = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )

                    if result.returncode != 0:
                        logger.error(f"FFmpeg multiplexing failed:\n{result.stderr}")
                        return False
                    logger.info(f"{Color.fg('light_gray')}Mixed flow completed: {Color.fg('black')}{temp_file_path}{Color.reset()}")
                    return True
                except Exception as e:
                    logger.error(f"FFmpeg mixing error: {str(e)}")
                    return False
            case "MKVTOOLNIX":
                MKVTOOLNIX_path: Path = Route().mkvmerge_path
                if not MKVTOOLNIX_path.exists():
                    if paramstore.get("mkvmerge_path_ok") is True:
                        MKVTOOLNIX_path_str: str = "mkvmerge"
                    else:
                        logger.error(f"mkvmerge.exe not found at: {MKVTOOLNIX_path}")
                        return False
                else:
                    MKVTOOLNIX_path_str: str = get_short_path_name(MKVTOOLNIX_path)
                
                # 轉換檔案路徑為短路徑
                video_short: str = get_short_path_name(Path(video_file_str))
                audio_short: str = get_short_path_name(Path(audio_file_str))
                output_short: str = get_short_path_name(temp_file_path.parent) + "\\" + temp_file_path.name
                
                # 建立基本命令
                cmd = [
                    MKVTOOLNIX_path_str,
                    "-o",
                    output_short,
                    video_short,
                    audio_short,
                ]

                # 如果有字幕，加入字幕混流參數
                if self.subs_successful != []:  # subs_successful 是回傳subdl.py list[tuple[str, str, Path]]
                    for lang, sub_m3u8_url, subtitle_path in self.subs_successful:
                        subtitle_short: str = get_short_path_name(subtitle_path)
                        cmd.extend([
                            "--language", f"0:{lang}",
                            subtitle_short
                        ])

                try:
                    logger.info(f"{Color.fg('light_gray')}Start using mkvmerge to mux video and audio...{Color.reset()}")
                    result: subprocess.CompletedProcess = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )

                    if result.returncode != 0:
                        logger.error(f"mkvmerge multiplexing failed:\n{result.stderr}")
                        return False
                    logger.info(f"{Color.fg('gray')}Mixed flow completed: {temp_file_path}{Color.reset()}")
                    return True
                except Exception as e:
                    logger.error(f"mkvmerge mixing error: {str(e)}")
                    return False
            case _:
                logger.error(f"Unsupported mux tool: {mux_tool}")
                return False

    async def build_ffmpeg_command(
        self,
        video_file: str,
        audio_file: str | None,
        temp_file_path: Path,
        FFMPEG_path: str,
    ) -> list[str]:

        # 轉換檔案路徑為短路徑
        video_short: str = get_short_path_name(Path(video_file))
        output_short: str = get_short_path_name(temp_file_path.parent) + "\\" + temp_file_path.name
        
        command: list[str] = [
            FFMPEG_path,
            "-i",
            video_short,
        ]

        input_index: int = 1
        
        if audio_file is not None:
            audio_short: str = get_short_path_name(Path(audio_file))
            command.extend(["-i", audio_short])
            input_index += 1

        subtitle_start_index: int = input_index

        if self.subs_successful and CFG['Container']['video'].strip().lower() == "mkv":
            # 先把每個字幕檔加入為 ffmpeg 的輸入 並同步遞增 input_index
            for _, _, subtitle_path in self.subs_successful:
                subtitle_short: str = get_short_path_name(subtitle_path)
                command.extend(["-i", subtitle_short])
                input_index += 1

            # 再為每個已加入的字幕建立 -map 與語言 metadata
            for idx, (lang, _, _) in enumerate(self.subs_successful):
                # 取前兩個字元作為語言代碼 若不足或非字母則回退為 'und'
                lang_code = (lang or "").strip().lower()[:2]
                if not lang_code.isalpha():
                    lang_code = "und"

                command.extend([
                    "-map", f"{subtitle_start_index + idx}:s",
                    "-c:s", "copy",
                    f"-metadata:s:s:{idx}", f"language={lang_code}"
                ])

        command.extend(["-map", "0:v"])
        
        if audio_file is not None:
            command.extend(["-map", "1:a"])

        command.extend([
            "-c", "copy",
            "-buffer_size", "32M",
            "-y",
            output_short,
        ])

        return command
