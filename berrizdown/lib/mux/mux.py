import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from lib.__init__ import container
from lib.load_yaml_config import CFG, ConfigLoader
from static.color import Color
from static.parameter import paramstore
from static.route import Route
from unit.handle.handle_log import setup_logging

logger = setup_logging("mux", "lavender")


class FFmpegMuxer:
    base_dir: Path
    decryption_key: list[Any] | None

    def __init__(self, base_dir: Path, isdrm: bool, decryption_key: list[str] | None = None):
        self.base_dir: Path = base_dir
        self.decryption_key: list[str] | None = decryption_key
        self.key: str = None
        self.input_path: Path = None
        self.output_path: Path = None
        self.isdrm: bool = isdrm

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

    async def decrypt(
        self,
    ) -> bool:
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
        mp4decrypt_path = Route().mp4decrypt_path

        if not mp4decrypt_path.exists():
            logger.error(f"mp4decrypt.exe not found at: {mp4decrypt_path}")
            return False

        try:
            # 分割 key 字串並為每個 key 添加 --key 參數
            key_parts: list[str] = self.key.split()
            key_args: list[str] = []
            for k in key_parts:
                key_args.extend(["--key", k])

            # 建立完整的命令
            command: list[str] = [str(mp4decrypt_path)] + key_args + [str(self.input_path), str(self.output_path)]

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Decryption failed for {self.input_path}: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error decrypting {self.input_path}: {str(e)}")
            return False

    async def _decrypt_file_packager(self) -> bool:
        packager_path = Route().packager_path
        packager_output_path = Path(self.output_path).with_suffix(".m4v")

        if not packager_path.exists():
            if paramstore.get("packager_path_ok") is True:
                packager_path: str = "packager"
            else:
                logger.error(f"shaka-packager.exe not found at: {packager_path}")
                return False

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
            str(packager_path),
            f"input={self.input_path},stream_selector=0,output={packager_output_path}",
            "--enable_raw_key_decryption",
        ] + key_args

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug(f"Packager output: {result.stdout}")

            # 成功後.m4v 改回指定副檔名
            final_output_path = packager_output_path.with_suffix(f".{container}")
            packager_output_path.rename(final_output_path)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Packager failed: {e.stderr}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error running packager: {e}")
            return False

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
        MKVTOOLNIX_path: Path = Route().mkvmerge_path
        if not MKVTOOLNIX_path.exists():
            if paramstore.get("mkvmerge_path_ok") is True:
                MKVTOOLNIX_path: str = "mkvmerge"
            else:
                logger.error(f"mkvmerge.exe not found at: {MKVTOOLNIX_path}")
                return False
        FFMPEG_path: Path = Route().ffmpeg
        if not FFMPEG_path.exists():
            if paramstore.get("ffmpeg_path_ok") is True:
                FFMPEG_path: str = "ffmpeg"
            else:
                logger.error(f"ffmpeg.exe not found at: {FFMPEG_path}")
                return False
        match mux_tool:
            case "FFMPEG":
                cmd: list[str] = await self.build_ffmpeg_command(video_file_str, audio_file_str, temp_file_path, FFMPEG_path)

                try:
                    logger.info(f"{Color.fg('firebrick')}Start using FFmpeg to mux video and audio...{Color.reset()}")
                    result: subprocess.CompletedProcess = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
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
                cmd = [
                    MKVTOOLNIX_path,
                    "-o",
                    str(temp_file_path),
                    str(Path(video_file_str)),
                    str(Path(audio_file_str)),
                ]
                try:
                    logger.info(f"{Color.fg('light_gray')}Start using mkvmerge to mux video and audio...{Color.reset()}")
                    result: subprocess.CompletedProcess = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
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
        FFMPEG_path: Path,
    ) -> list[str]:
        """
        建立 FFmpeg 命令，用於混流 video + audio 或僅封裝 video
        所有輸出皆為 copy 模式，無轉碼
        """
        command: list[str] = [
            FFMPEG_path,
            "-i",
            video_file,
        ]

        if audio_file is not None:
            command += ["-i", audio_file]

        command += [
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            "-buffer_size",
            "32M",
            "-fflags",
            "+genpts",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-metadata",
            "title=",
            "-metadata",
            "comment=",
            "-y",
            str(temp_file_path),
        ]

        return command
