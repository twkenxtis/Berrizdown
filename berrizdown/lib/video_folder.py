import time
from datetime import datetime
from functools import cached_property
from uuid import UUID

import aiofiles.os as aios
from static.color import Color
from static.parameter import paramstore
from static.PublicInfo import PublicInfo
from unit.__init__ import FilenameSanitizer
from unit.community.community import custom_dict, get_community
from unit.handle.handle_log import setup_logging

from lib.__init__ import File_date_time_formact, OutputFormatter, dl_folder_name, get_artis_list, move_contents_to_parent, printer_video_folder_path_info
from lib.load_yaml_config import CFG
from lib.name_metadata import meta_name
from lib.path import Path

logger = setup_logging("video_folder", "chocolate")


class Video_folder:
    def __init__(self, public_info: PublicInfo, input_community_name: str) -> None:
        self.artis_list: list[dict[str, str | None]] = public_info.artists
        self.community_id: str | int | None = public_info.community_id
        self.FilenameSanitizer = FilenameSanitizer.sanitize_filename
        self.folder_name: str = ""
        self.input_community_name: str | int | None = input_community_name
        self.media_id: UUID | None = public_info.media_id

        self._public_info = public_info

    @cached_property
    def FDT(self) -> File_date_time_formact:
        return File_date_time_formact(self._public_info, "VOD_LIVE")

    @cached_property
    def get_artis(self) -> str:
        return get_artis_list(self.artis_list)

    @cached_property
    def title(self) -> str:
        return self.FilenameSanitizer(self._public_info.title)

    @cached_property
    def time_str(self) -> str:
        return self.FDT.vod_live_time_str()

    async def get_custom_community_name(self) -> tuple[str | None, str | int | None]:
        community_name_result = await self.get_community_name()
        if community_name_result is not None:
            custom_community_name = await custom_dict(community_name_result)
        else:
            custom_community_name = None
        community_name: str | int | None = await get_community(self.community_id) or self.input_community_name
        return custom_community_name, community_name

    async def get_community_name(self) -> str | int | None:
        community_name: str | int | None = await get_community(self.community_id) or self.input_community_name
        return community_name

    def get_base_dir(self, community_name: str, custom_community_name: str) -> Path:
        if custom_community_name is not None:
            cm_folder_name: str = custom_community_name
        elif community_name is not None:
            cm_folder_name: str = community_name
        elif self.input_community_name is not None:
            cm_folder_name: str = self.input_community_name
        else:
            logger.warning("Community name not found, using 'Unknown Artis' instead.")
            cm_folder_name: str = "Unknown Artis"
        cm_folder_name = self.FilenameSanitizer(cm_folder_name)
        if paramstore.get("savedir") is not None:
            return Path(paramstore.get("savedir")).parent / self.FilenameSanitizer(Path(paramstore.get("savedir")).name) / cm_folder_name / "Videos"
        else:
            return Path.cwd() / Path(dl_folder_name) / cm_folder_name / "Videos"

    async def video_folder_handle(self, custom_community_name: str, community_name: str) -> Path:
        """根據 community_name 和媒體資訊建立下載資料夾路徑"""
        base_dir: Path = self.get_base_dir(community_name, custom_community_name)
        self.base_dir = base_dir
        temp_folder_name: str = f"temp_{self.time_str}_{self.media_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        temp_name: str = self.FilenameSanitizer(temp_folder_name)
        temp_dir: Path = Path.cwd() / base_dir / temp_name / f"temp_{self.time_str}_{self.media_id}"
        temp_dir.mkdirp()
        self.output_dir = Path(temp_dir.resolve())
        video_meta: dict[str, str] = meta_name(
            self.time_str,
            self.title,
            custom_community_name or community_name or self.input_community_name or "Unknown Community",
            self.get_artis,
        )
        folder_name: str = OutputFormatter(f"{CFG['donwload_dir_name']['dir_name']}").format(video_meta)
        self.folder_name: str = folder_name  # for final using folder name for self
        return self.output_dir  # for Download reutrn temp folder name path

    def get_unique_folder_name(self, base_name: str, full_path: Path) -> Path:
        """確保資料夾名稱唯一性，避免衝突"""
        base_name = self.FilenameSanitizer(base_name)
        new_path: Path = Path(full_path).parent / base_name
        counter: int = 1
        while new_path.exists():
            new_path = Path(full_path).parent / f"{base_name} ({counter})"
            counter += 1
        return new_path

    async def re_name_folder(self, video_file_name: str, mux_bool_status: bool) -> None:
        """將下載完成後的暫存資料夾名稱重新命名為最終標題"""
        skip_conditions = [
            paramstore.get("video_dl_cancelled"),
            paramstore.get("skip_merge"),
            paramstore.get("skip_mux"),
        ]
        # 是否扁平化子資料夾並執行
        if self._should_flatten_subfolder(skip_conditions, mux_bool_status):
            await self._flatten_to_parent(video_file_name)
            return
        # 檢查 output_dir 是否設定
        if not self._validate_output_dir():
            return
        # 準備路徑與前置檢查
        new_path, full_path, original_name = self._prepare_paths()
        if not self._ensure_uuid_in_original_name(original_name):
            return
        # 刪除暫存資料夾 merge mux false
        await self._delete_temp_if_needed(full_path, mux_bool_status)
        # 取得唯一新路徑並執行重命名
        new_path = self.get_unique_folder_name(self.folder_name, new_path)
        await self._rename_with_retries(full_path, new_path)
        # 列印路徑資訊
        self._print_path_info(skip_conditions, new_path, video_file_name)

    def _should_flatten_subfolder(self, skip_conditions: list, mux_bool_status: bool) -> bool:
        return paramstore.get("nosubfolder") is True and not any(skip_conditions) and mux_bool_status is True

    async def _flatten_to_parent(self, video_file_name: str) -> None:
        logger.info(f"{Color.fg('light_gray')}No subfolder for{Color.reset()} {Color.fg('light_gray')}Video")
        if Path(self.output_dir).is_dir():
            await move_contents_to_parent(
                Path(self.output_dir).parent,
                video_file_name,
                f"{Color.fg('light_amber')}Video {Color.reset()}",
            )

    def _validate_output_dir(self) -> bool:
        if self.output_dir is None:
            logger.warning("Output directory not set, skipping folder rename.")
            return False
        return True

    def _prepare_paths(self) -> tuple[Path, Path, str]:
        new_path: Path = self.base_dir / self.folder_name
        full_path: Path = Path.cwd() / Path(self.output_dir)
        original_name: str = full_path.parent.name
        return new_path, full_path, original_name

    def _ensure_uuid_in_original_name(self, original_name: str) -> bool:
        if str(self.media_id) not in original_name:
            logger.warning(f"UUID '{self.media_id}' not found in folder name: {original_name}")
            return False
        return True

    async def _delete_temp_if_needed(self, full_path: Path, mux_bool_status: bool) -> None:
        if mux_bool_status is True:
            await self.del_temp_folder(full_path)

    async def _rename_with_retries(self, full_path: Path, new_path: Path) -> None:
        max_retries: int = 3
        delay_seconds: float = 0.25
        for attempt in range(1, max_retries + 1):
            try:
                await aios.rename(full_path.parent, new_path)
                logger.info(f"{Color.fg('light_blue')}Renamed folder From: {Color.reset()}{Color.fg('light_gray')}{full_path.parent} {Color.fg('dark_green')}{new_path}{Color.reset()}")
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"All {max_retries} retries failed. Last error: {e}")
                else:
                    logger.warning(f"Attempt {attempt} failed: {e}.")
                    logger.info(f"Retrying in {Color.fg('mist')}{delay_seconds}s {Color.reset()}")
                    time.sleep(delay_seconds)

    def _print_path_info(self, skip_conditions: list, new_path: Path, video_file_name: str) -> None:
        if not all(skip_conditions):
            printer_video_folder_path_info(
                new_path,
                video_file_name,
                f"{Color.fg('light_amber')}Video {Color.reset()}",
            )

    async def del_temp_folder(self, temp_path: Path) -> None:
        """刪除下載完成後的 'temp' 暫存資料夾"""
        try:
            if temp_path.exists():
                if temp_path.exists() and (paramstore.get("skip_merge") is None and paramstore.get("skip_mux") is None):
                    await aios.rmdir(temp_path)
                else:
                    await aios.rename(temp_path, temp_path.parent / self.folder_name)
        except TypeError:
            pass
        except OSError:
            pass
