import asyncio
import shutil

from typing import Any

from berrizdown.lib.__init__ import container
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.path import Path
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.handle.handle_log import setup_logging


logger = setup_logging("clean_files", "daffodil")


class CleanFiles:
    def __init__(self, dl_obj: Any, base_dir: Path, decryption_key: str | None = None, nosubfolder_flag: bool = False) -> None:
        self.dl_obj: object = dl_obj
        self.base_dir: Path = base_dir
        self.decryption_key: str | None = decryption_key
        self.nosubfolder_flag: bool = nosubfolder_flag
        
    async def clean_file(self) -> None:
        """清理下載過程中的暫存檔案、加密檔案和暫存目錄"""
        base_dir: Path = self.base_dir
        if base_dir.exists():
            file_paths: list[Path] = []
            if self.nosubfolder_flag is False:
                if len(self.dl_obj.__dict__.get("subtitle")) != 0 and CFG['Container']['video'] == ("mkv" or "mp4") and\
                    paramstore.get("keep-subs") is not True and paramstore.get("subs_only") is not True:
                    try:
                        for lang in self.dl_obj.__dict__.get("subtitle"):
                            logger.info(f"Removed subtitle file: {Color.fg('mist')}{self.dl_obj.__dict__.get("subtitle").get(lang)}{Color.reset()}")
                            self.dl_obj.__dict__.get("subtitle").get(lang).unlink()
                    except Exception as e:
                        logger.error(f"Error removing subtitle file: {e}")
                        
            if self.decryption_key is None:
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
                    
            for subfolder in ["audio", "video", "subtitle"]:
                if self.nosubfolder_flag is True and paramstore.get("nosubfolder") is True:
                    shutil.rmtree(base_dir / Path(subfolder).parent, ignore_errors=True)
                else:
                    dir_path: Path = base_dir / Path(subfolder)
                        
                    try:
                        await asyncio.to_thread(shutil.rmtree, dir_path)
                        logger.info(f"Force-removed directory: {Color.fg('mist')}{dir_path}{Color.reset()}")
                    except FileNotFoundError:
                        logger.info(f"Directory not found, skipping: {dir_path}")
                    except Exception as e:
                        logger.error(f"Error force-removing directory {dir_path}: {e}")