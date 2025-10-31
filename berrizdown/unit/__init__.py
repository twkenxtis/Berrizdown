import asyncio
import re
import unicodedata
from functools import lru_cache

import aiofiles
import httpagentparser
import yaml
from fake_useragent import UserAgent
from lib.path import Path
from static.color import Color
from static.version import __version__

from unit.handle.handle_log import setup_logging

logger = setup_logging("unit.__init__", "green")

try:
    from static.route import Route
except FileNotFoundError as e:
    logger.error(e)


YAML_PATH: Path = Route().YAML_path


class ConfigLoader:
    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: Path = YAML_PATH) -> dict:
        config = asyncio.run(cls._load_async(path))
        return config

    @staticmethod
    async def _load_async(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        async with aiofiles.open(path, encoding="utf-8") as f:
            raw = await f.read()

        try:
            return yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}")


CFG = ConfigLoader.load()


def is_user_agent(ua: str) -> bool:
    if not ua or not isinstance(ua, str):
        return False
    parsed = httpagentparser.detect(ua)
    return bool(parsed.get("platform") or parsed.get("browser"))


def get_useragent() -> str:
    USERAGENT = CFG["headers"]["User-Agent"]
    fakseua = CFG["headers"]["Fake-User-Agent"]
    try:
        if USERAGENT is None:
            raise AttributeError
        if is_user_agent(USERAGENT) is False:
            raise AttributeError
        if not isinstance(fakseua, bool):
            raise AttributeError
        if fakseua is True:
            ua = UserAgent(platforms="mobile")
            USERAGENT = ua.random
    except AttributeError:
        logger.warning(f"Unsupported User-Agent: {Color.bg('ruby')}{USERAGENT}{Color.fg('gold')}, try using Berrizdown/{__version__} to continue ...")
        USERAGENT = f"Berrizdown/{__version__}"
        logger.info(USERAGENT)
    return USERAGENT


USERAGENT = get_useragent()


class FilenameSanitizer:
    MAX_FILENAME_LENGTH = 200
    MAX_PATH_LENGTH = 255

    # Windows 保留名稱
    WINDOWS_RESERVED_NAMES = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    # Windows 非法字符: <>:"/\|?* 和控製字符 \x00-\x1F
    # Linux 額外非法字符: / 和 \x00
    ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1F]'

    # 潛在問題字符：通常在 Shell/Script 中有特殊含義
    # 移除了 \s (空格) 以便單獨處理
    PROBLEMATIC_CHARS_NOSPC = r"[&$`!*?;{}()\[\]~#%\']"

    @staticmethod
    def sanitize_filename(name: str | None, is_folder: bool = False) -> str:
        if name is None:
            return "None" if not is_folder else "empty_folder"
        if not isinstance(name, str):
            name = str(name)
        name = name.strip()
        if not name:
            return "None" if not is_folder else "empty_folder"
        if len(name) > FilenameSanitizer.MAX_PATH_LENGTH:
            logger.warning(f"Path too long, truncated: {name}")
            name = name[: FilenameSanitizer.MAX_PATH_LENGTH]
        # NFD 非正規化分解 解決漢字「ㄅ」變成「ㄅ ㄆ」的問題
        # NFC 強製轉換 解決韓文「냥」變成「ᄂ ᆼ」的正規化問題
        name = unicodedata.normalize("NFC", name)
        name = re.sub(FilenameSanitizer.ILLEGAL_CHARS, "", name)
        name = re.sub(FilenameSanitizer.PROBLEMATIC_CHARS_NOSPC, "", name)
        name = name.strip()
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"^[.\s]+", "", name)
        name = re.sub(r"[.\s]+$", "", name)

        if not name:
            return "None" if not is_folder else "empty_folder"
        base_name = name
        ext = ""
        if "." in name and not is_folder:
            base_name, ext = name.rsplit(".", 1)
        upper_base = base_name.upper()
        if upper_base in FilenameSanitizer.WINDOWS_RESERVED_NAMES:
            name = f"_{name}"
            logger.info(f"Reserved name detected, prefixed with underscore: {name}")
        if name.startswith("-"):
            name = f"_{name[1:]}"
            logger.info(f"Leading hyphen detected, prefixed with underscore: {name}")
        if not name:
            return "None" if not is_folder else "empty_folder"
        if len(name) > FilenameSanitizer.MAX_FILENAME_LENGTH:
            logger.warning(f"Filename too long, truncated: {name}")
            if ext and not is_folder:
                max_base_len = FilenameSanitizer.MAX_FILENAME_LENGTH - len(ext) - 1
                name = name[:max_base_len] + "." + ext
            else:
                name = name[: FilenameSanitizer.MAX_FILENAME_LENGTH]
        return name
