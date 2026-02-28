import asyncio
import ctypes
import subprocess
from typing import Any
from pathlib import Path

from rich.console import Console
from rich.progress import SpinnerColumn, TextColumn, Progress

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
        return long_path_str
    
    # 建立緩衝區並取得短路徑
    buffer = ctypes.create_unicode_buffer(buffer_size)
    ctypes.windll.kernel32.GetShortPathNameW(long_path_str, buffer, buffer_size)
    
    return buffer.value


class FFmpegMuxer:
    base_dir: Path
    decryption_key: list[Any] | None

    def __init__(
        self,
        base_dir: Path,
        temp_mux_path: Path,
        isdrm: bool,
        subs_successful: list[tuple[str, str, Path]]|list,
        dl_obj,
        decryption_key: list[str] | None = None,
        ):
        self.dl_obj :object = dl_obj
        self.base_dir: Path = base_dir
        self.decryption_key: list[str] | None = decryption_key
        self.key: str = None
        self.input_path: Path = None
        self.output_path: Path = None
        self.temp_mux_path: Path = temp_mux_path
        self.isdrm: bool = isdrm
        self.subs_successful: list[tuple[str, str, Path]]|list = subs_successful
        self.short_input_output_path_dict: dict[str, str] = {}

    async def mux_main(self) -> bool:

        if paramstore.get("nodl") is True:
            logger.info(f"{Color.fg('light_gray')}Skip downloading{Color.reset()}")
            return True
        elif paramstore.get("skip_merge") is True:
            logger.info(f"{Color.fg('light_gray')}Skip muxing{Color.reset()}")
            return False
        
        console: Console = Console()
        
        progress: Progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        
        try:
            for track_type in ("video", "audio"):
                self.input_path: Path | None = getattr(self.dl_obj, track_type, None)
                if self.input_path is None:
                    continue

                if not self.input_path.exists():
                    return False

                if self.isdrm:
                    await self.decryption_track(track_type, progress, loop)
        except Exception:
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
        elif paramstore.get("skip_mux") is True or paramstore.get("nodl") is True:
            return True
        else:
            video_short: str = get_short_path_name(self.dl_obj.video)
            audio_short: str = get_short_path_name(self.dl_obj.audio)
            output_short: str = get_short_path_name(self.temp_mux_path)
            self.short_input_output_path_dict: dict[str, str] = {
                "video": video_short,
                "audio": audio_short,
                "output": output_short,
            }
            return await self.choese_mux_tool(progress, loop)

    async def choese_mux_tool(self, progress: Progress, loop: asyncio.AbstractEventLoop):
        try:
            mux_tool: str = CFG["Container"]["mux"]
            mux_tool: str = mux_tool.upper()
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
                    
                cmd: list[str] = await self.build_ffmpeg_command(FFMPEG_path_str)

                try:
                    logger.info(f"{Color.fg('firebrick')}Start using FFmpeg to mux video and audio...{Color.reset()}")
                    
                    with progress:
                        task_id = progress.add_task(description="[cyan]Using FFmpeg mux...[/cyan]", total=None)
                        
                        result: subprocess.CompletedProcess = await loop.run_in_executor(
                            None,
                            lambda: subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                            )
                        )
                        progress.update(task_id, description="[green]FFmpeg mux complete！[/green]")

                        if result.returncode != 0:
                            logger.error(f"FFmpeg multiplexing failed:\n{result.stderr}")
                            return False
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
                
                # 建立基本命令
                cmd = [
                    MKVTOOLNIX_path_str,
                    "-o",
                    self.short_input_output_path_dict.get("output"),
                    self.short_input_output_path_dict.get("video"),
                    self.short_input_output_path_dict.get("audio"),
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
                    
                    with progress:
                        task_id = progress.add_task(description="[cyan]Using mkvmerge mux...[/cyan]", total=None)
                        
                        result: subprocess.CompletedProcess = await loop.run_in_executor(
                            None,
                            lambda: subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                            )
                        )
                        progress.update(task_id, description="[green]mkvmerge mux complete！[/green]")

                    if result.returncode != 0:
                        logger.error(f"mkvmerge multiplexing failed:\n{result.stderr}")
                        return False
                    logger.info(f"{Color.fg('gray')}Mixed flow completed: {self.temp_mux_path}{Color.reset()}")
                    return True
                except Exception as e:
                    logger.error(f"mkvmerge mixing error: {str(e)}")
                    return False
            case _:
                logger.error(f"Unsupported mux tool: {mux_tool}")
                return False

    async def decryption_track(self, track_type: str, progress: Progress, loop: asyncio.AbstractEventLoop) -> Path | None:
        """Handle decryption if needed and return final file path"""
        decryption_key: str = await self.process_decryption_key()
        decrypted_file: Path = self.input_path.parent / f"{track_type}_decrypted.{container}"

        self.key: str | None = decryption_key
        self.output_path: Path = Path(get_short_path_name(decrypted_file))
        
        if await self.decrypt(track_type, progress, loop):
            # 更新新的解密路徑到dataclass物件            
            self.dl_obj.audio = decrypted_file if track_type == "audio" else self.dl_obj.audio
            self.dl_obj.video = decrypted_file if track_type == "video" else self.dl_obj.video
            return decrypted_file
        return None

    async def process_decryption_key(self) -> str:
        if type(self.decryption_key) is list:
            key: str = " ".join([str(sublist).replace("[", "").replace("]", "") for sublist in self.decryption_key])
            return key
        elif type(self.decryption_key) is str:
            return self.decryption_key
        return ""

    async def decrypt(self, track_type: str, progress: Progress, loop: asyncio.AbstractEventLoop) -> bool:
        try:
            decryptionengine: str = CFG["Container"]["decryption-engine"]
            decryptionengine: str = decryptionengine.upper()
        except AttributeError:
            ConfigLoader.print_warning("decryptionengine", decryptionengine, "shaka-packager")
            # decryptionengine = "MP4DECRYPT"
            decryptionengine = "SHAKA_PACKAGER"
            
        input_short: str = get_short_path_name(self.input_path)
        
        match decryptionengine:
            case "MP4DECRYPT":
                return await self._decrypt_file_mp4decrypt(input_short, progress, track_type, loop)
            case "SHAKA_PACKAGER":
                return await self._decrypt_file_packager(input_short, progress, track_type, loop)
            case _:
                ConfigLoader.print_warning("decryptionengine", decryptionengine, "shaka-packager")
                return await self._decrypt_file_packager(input_short, progress, track_type, loop)

    async def _decrypt_file_mp4decrypt(
        self, input_short: str, progress: Progress, track_type: str, loop: asyncio.AbstractEventLoop) -> bool:
        mp4decrypt_path: Path = Route().mp4decrypt_path
        if not mp4decrypt_path.exists():
            logger.error(f"mp4decrypt.exe not found at: {mp4decrypt_path}")
            return False

        try:
            mp4decrypt_short: str = get_short_path_name(mp4decrypt_path)
            
            # 分割 key 字串並為每個 key 添加 --key 參數
            key_parts: list[str] = self.key.split()
            key_args: list[str] = []
            for k in key_parts:
                key_args.extend(["--key", k])

            # 建立完整的命令
            command: list[str] = [mp4decrypt_short] + key_args + [input_short, self.output_path]
            
            with progress:
                task_id = progress.add_task(
                        description=f"[cyan] mp4decrypt in progress: [/cyan][blue]{track_type}[/blue]", 
                    total=None
                )
                
                await loop.run_in_executor(
                    None, 
                    lambda: subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                )
                progress.update(task_id, description=f"[green]　Decryption complete: [/green][blue]{track_type}[/blue]\n[yellow]{self.key}[/yellow]")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Decryption failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False

    async def _decrypt_file_packager(
        self, input_short: str, progress: Progress, track_type: str, loop: asyncio.AbstractEventLoop) -> bool:
            packager_path: Path = Route().packager_path
            packager_output_path: Path = Path(self.output_path).with_suffix(".m4v")

            # 檢查路徑邏輯
            if not packager_path.exists():
                if paramstore.get("packager_path_ok") is True:
                    packager_path_str = "packager"
                else:
                    logger.error(f"shaka-packager.exe not found at: {packager_path}")
                    return False
            else:
                packager_path_str: str = get_short_path_name(packager_path)

            # 處理 Key 的邏輯
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
                f"input={input_short},stream_selector=0,output={packager_output_path}",
                "--enable_raw_key_decryption",
            ] + key_args

            try:
                logger.debug(f"Packager command: {' '.join(command)}")
                
                with progress:
                    task_id = progress.add_task(
                        description=f"[cyan]　shaca-packager in progress: [/cyan][blue]{track_type}[/blue]", 
                        total=None
                    )
                    
                    await loop.run_in_executor(
                        None,
                        lambda: subprocess.run(
                            command,
                            check=True,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                        )
                    )
                    
                    progress.update(task_id, description=f"[green]　Decryption complete: [/green][blue]{track_type}[/blue]\n[yellow]{self.key}[/yellow]")

            except subprocess.CalledProcessError as e:
                logger.error(f"Packager failed: {e.stderr}")
                return False
            except Exception as e:
                logger.exception(f"Unexpected error running packager: {e}")
                return False
            
            # 成功後.m4v 改回指定副檔名
            final_output_path: Path = packager_output_path.with_suffix(f".{container}")
            try:
                packager_output_path.rename(final_output_path)
            except Exception as e:
                logger.error(f"Failed to rename {packager_output_path} to {final_output_path}: {e}")
                return False
                
            return True

    async def build_ffmpeg_command(self, FFMPEG_path: str) -> list[str]:
        
        command: list[str] = [
            FFMPEG_path,
            "-i",
            self.short_input_output_path_dict.get("video"),
        ]

        input_index: int = 1
        
        if self.short_input_output_path_dict.get("audio") is not None:
            command.extend(["-i", self.short_input_output_path_dict.get("audio")])
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
        
        if self.short_input_output_path_dict.get("audio") is not None:
            command.extend(["-map", "1:a"])

        command.extend([
            "-c", "copy",
            "-buffer_size", "32M",
            "-y",
            self.short_input_output_path_dict.get("output"),
        ])

        return command
