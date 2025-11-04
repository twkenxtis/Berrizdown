from __future__ import annotations

import asyncio
import re
import shutil
import string
from concurrent.futures import ThreadPoolExecutor
from functools import cache, lru_cache

from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.date.date import get_formatted_publish_date, get_timestamp_formact
from berrizdown.unit.handle.handle_log import setup_logging

from berrizdown.lib.load_yaml_config import CFG, ConfigLoader
from berrizdown.lib.name_metadata import meta_name
from berrizdown.lib.path import Path

logger = setup_logging("lib.__init__", "fern")
executor = ThreadPoolExecutor()


@lru_cache(maxsize=1)
def get_container(yaml_container=CFG["Container"]["video"]) -> str:
    try:
        container = yaml_container.strip().lower().replace(".", "")
    except AttributeError:
        ConfigLoader.print_warning("Container", yaml_container, "MKV")
        return "mkv"

    if container not in ("ts, mp4, mov, m4v, mkv, avi"):
        logger.warning(f"invaild container {container}, auto choese mkv to communite!")
        return "mkv"
    match CFG["Container"]["mux"]:
        case "mkvtoolnix":
            return "mkv"
        case _:
            return container


container = get_container()


@lru_cache(maxsize=1)
def get_download_folder_name(
    yaml_container=CFG["donwload_dir_name"]["download_dir"],
) -> str:
    folder_name = FilenameSanitizer.sanitize_filename(yaml_container)
    return folder_name


dl_folder_name = get_download_folder_name()


def use_proxy_list(yaml_container=CFG["Proxy"]["Proxy_Enable"]) -> bool:
    return bool(yaml_container)


use_proxy = use_proxy_list()


class OutputFormatter:
    def __init__(self, template: str) -> None:
        self.original_template = template
        self.template = template
        self.fields = self.extract_fields(template)
        self._cache: dict[str, str] = {}

    def format(self, metadata: dict[str, str]) -> str:
        # 建立 metadata 的快取 key
        cache_key = str(sorted(metadata.items()))
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 重設 template
        self.template = self.original_template
        safe_meta = {field: metadata.get(field, "") for field in self.fields}

        for field in [f for f in self.fields if f != "title"]:
            if safe_meta.get(field, "") == "":
                self.template = self._remove_field_segment(self.template, field)

        result = self.template.format(**safe_meta)
        result = re.sub(r"\s+", " ", result).strip()
        self._cache[cache_key] = result
        return result

    def extract_fields(self, template: str) -> list[str]:
        formatter = string.Formatter()
        return [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]

    def _remove_field_segment(self, template: str, field: str) -> str:
        pattern = rf"[\s\-._]*{{{field}}}[\s\-._]*"
        return re.sub(pattern, " ", template)


FetcherType = object | dict


class File_date_time_formact:
    def __init__(
        self,
        fetcher: FetcherType,
        type: str,
        community_name: str|None = None,
        input_community_name: str|None = None,
    ) -> None:
        self.fm = CFG["output_template"]["date_formact"]
        self.fmt: str = get_timestamp_formact(self.fm)  # %y%m%d_%H-%M
        self.community_name: str = community_name or input_community_name
        match type:
            case "NOTICE":
                self.nfetcher: object = fetcher
                self.ntitle: str = self.nfetcher.get_title()
                self.reservedAt: str = self.nfetcher.get_reservedAt()
                self.ntime_str: str = get_formatted_publish_date(self.reservedAt, self.fmt)
                self.ninput_community_name: str = input_community_name
            case "POST":
                self.btitle: str = fetcher["title"]
                self.updatedAt: str = fetcher["index"]["post"]["updatedAt"]
                self.btime_str: str = get_formatted_publish_date(self.updatedAt, self.fmt)
                self.get_writer_name: str = self.artis_name(fetcher["writer_name"])
            case "VOD_LIVE":
                self.mfetcher: object = fetcher
                self.mpublished_at: str = fetcher.published_at

    @cache
    def artis_name(self, write_name: str) -> str:
        A: str = write_name
        if self.community_name == A:
            return A.lower()
        return A

    @lru_cache(maxsize=1)
    def notice(self) -> tuple[str, str]:
        """計算並快取 NOTICE 類型的 JSON 和 HTML 檔名"""
        notice_mata_data: dict[str, str] = meta_name(
            self.ntime_str,
            self.ntitle,
            self.community_name,
            self.ninput_community_name,
        )
        notice_json: str = OutputFormatter(f"{CFG['output_template']['json_file_name']}").format(notice_mata_data)
        notice_html: str = OutputFormatter(f"{CFG['output_template']['html_file_name']}").format(notice_mata_data)
        return notice_json, notice_html

    @lru_cache(maxsize=1)
    def post(self) -> tuple[str, str]:
        """計算並快取 POST 類型的 JSON 和 HTML 檔名"""
        post_mata_data: dict[str, str] = meta_name(self.btime_str, self.btitle, self.community_name, self.get_writer_name)
        post_json: str = OutputFormatter(f"{CFG['output_template']['json_file_name']}").format(post_mata_data)
        post_html: str = OutputFormatter(f"{CFG['output_template']['html_file_name']}").format(post_mata_data)
        return post_json, post_html

    @lru_cache(maxsize=1)
    def vod_live_time_str(self) -> str:
        mediatime_str: str = get_formatted_publish_date(self.mpublished_at, self.fmt)
        return mediatime_str


def get_artis_list(artis_list: list[dict[str, str | None]]) -> str:
    all_artis_list = set()
    for i in artis_list:
        if i.get("name"):
            all_artis_list.add(i["name"])
    all_artis_str: str = " ".join(sorted(all_artis_list)).strip()
    return all_artis_str


async def retry_async(fn, *args, **kwargs):
    MAX_RETRIES = 7
    RETRY_DELAY = 1
    for attempt in range(MAX_RETRIES):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                raise e


def sync_move(src: Path, dst: Path) -> str:
    shutil.move(str(src), str(dst))
    return dst.name


async def move(src: Path, stem: str, suffix: str, dst: Path, parent: Path, TAG: str) -> str:
    idx = 1
    while dst.exists():
        dst = parent / f"{stem} ({idx}){suffix}"
        idx += 1

    loop = asyncio.get_running_loop()
    moved_name = await retry_async(loop.run_in_executor, executor, sync_move, src, dst)
    skip_conditions = [
        paramstore.get("video_dl_cancelled"),
        paramstore.get("skip_merge"),
        paramstore.get("skip_mux"),
    ]
    if not all(skip_conditions):
        printer_video_folder_path_info(parent, moved_name, TAG)
    return moved_name


async def move_contents_to_parent(path: Path, file_name: str, TAG: str) -> None:
    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")

    parent = path.parent.parent
    tasks = []

    for item in path.rglob("*"):
        if item.is_file():
            stem, suffix = item.stem, item.suffix
            target = parent / item.name
            tasks.append(move(item, stem, suffix, target, parent, TAG))

    await asyncio.gather(*tasks)

    async def try_remove(p: Path):
        if p.exists() and p.is_dir() and p.name.startswith("temp_"):
            shutil.rmtree(p)
        if p.name == "Videos" and p.is_dir() and not any(p.iterdir()):
            shutil.rmtree(p)

    try:
        await retry_async(try_remove, path)
        await retry_async(try_remove, path.parent)
        file_name += f"\n{Color.fg('flamingo_pink')}No subfolders. All files are located in the top-level directory.{Color.reset()}"
    except Exception as e:
        raise RuntimeError(f"Failed to remove original folder {path}: {e}")


async def move_folder_to_parent(path: Path, file_name: str, TAG: str) -> Path:
    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")

    grandparent = path.parent.parent
    base_name = path.name
    idx = 0

    while True:
        suffix = f" ({idx})" if idx > 0 else ""
        target = grandparent / f"{base_name}{suffix}"
        if not target.exists():
            break
        idx += 1

    async def move_and_cleanup():
        shutil.move(str(path), str(target))
        cleanup_empty_parent(path.parent)

    try:
        await retry_async(asyncio.to_thread, move_and_cleanup)
        printer_video_folder_path_info(target, file_name, TAG)
        return target
    except Exception as e:
        raise RuntimeError(f"Failed to move folder {path} to {target}: {e}")


def cleanup_empty_parent(folder: Path) -> None:
    if folder.exists() and folder.is_dir() and not any(folder.iterdir()):
        shutil.rmtree(folder, ignore_errors=True)


def printer_video_folder_path_info(new_path: Path, video_file_name: str, TAG: str = None) -> None:
    if "Keep all segments in temp folder" in video_file_name:
        video_file_name = f"{video_file_name} → {new_path}\\temp"
    if paramstore.get("nodl") is True:
        logger.info(
            f"{Color.fg('tomato')}Skip downloading MODE "
            f"{Color.fg('yellow')}[The folder may be empty]: {Color.reset()}"
            f"{Color.fg('spring_aqua')}{Path(new_path)}\n　➥ {Color.fg('aquamarine')}{video_file_name}{Color.reset()}"
        )
    else:
        if TAG is None:
            TAG = f"{Color.fg('bright_magenta')}FILE {Color.reset()}"
        logger.info(f"{TAG}{Color.fg('yellow')}save to {Color.reset()}{Color.fg('spring_aqua')}{Path(new_path)}\n　➥ {Color.fg('aquamarine')}{video_file_name}{Color.reset()}")


async def resolve_conflict_path(input_path: Path | str) -> Path:
    path = Path(input_path) if not isinstance(input_path, Path) else input_path
    if not path.exists():
        return path

    parent = path.parent
    name = path.name

    # 判斷是否為檔案（有副檔名）或資料夾（無副檔名）
    if path.is_file():
        # 檔案：分離副檔名
        stem, suffix = name.rsplit(".", 1)
        suffix = "." + suffix
    else:
        # folder 整個 name 都是 stem，無副檔名
        stem = name
        suffix = ""

    # 嘗試解析 "(int)" 結尾
    if stem.endswith(")"):
        parts = stem.rsplit(" (", 1)
        if len(parts) == 2 and parts[1][:-1].isdigit():
            base_stem = parts[0]
            start_index = int(parts[1][:-1]) + 1
        else:
            base_stem = stem
            start_index = 1
    else:
        base_stem = stem
        start_index = 1

    async def try_until_timeout():
        existing_names = {p.name for p in parent.iterdir()}
        index = start_index
        while True:
            candidate_name = f"{base_stem} ({index}){suffix}"
            if candidate_name not in existing_names:
                return parent / candidate_name
            index += 1

    try:
        async with asyncio.timeout(9):
            return await try_until_timeout()
    except TimeoutError:
        raise FileExistsError(f"Timeout: Cannot resolve path conflict for {path} within 9 seconds")
