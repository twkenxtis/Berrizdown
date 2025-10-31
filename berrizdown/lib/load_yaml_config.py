import asyncio
import os
import re
import subprocess
import sys
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import aiofiles
import rich.traceback
from email_validator import EmailNotValidError, validate_email
from key.cdm_path import CDM_PATH
from ruamel.yaml import YAML
from static.color import Color
from static.parameter import paramstore
from static.route import Route
from static.version import __version__
from unit.handle.handle_log import setup_logging

from lib.path import Path

rich.traceback.install()
logger = setup_logging("load_yaml_config", "fresh_chartreuse")


YAML_PATH: Path = Route().YAML_path


DEFAULT_UA = f"Berrizdown/{__version__}"


def check_email(email_str: str) -> bool:
    try:
        validate_email(email_str)
        return True
    except EmailNotValidError as e:
        logger.error(f"Mail invaild:  '{email_str}' | {e}")
        return False


def _check_tool_version(command_list: list) -> bool:
    try:
        result = subprocess.run(
            command_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


class ConfigLoader:
    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: Path = YAML_PATH) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        """同步介面，快取並返回完整、驗證過的 config 字典"""
        config = asyncio.run(cls._load_async(path))
        try:
            cls.check_cfg(config)
        except Exception as e:
            logger.error(f"{Color.fg('black')}Failed to load config: {e}{Color.reset()}")
            sys.exit(1)
        return config

    @staticmethod
    async def _load_async(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        async with aiofiles.open(path, encoding="utf-8") as f:
            raw = await f.read()

        try:
            return YAML().load(raw)
        except ValueError as e:
            raise ValueError(f"Failed to parse YAML: {e}")

    @staticmethod
    def print_warning(invaild_message: str, invaild_value: Any, correct_message: str) -> None:
        logger.warning(
            f"Unsupported value {Color.bg('ruby')}{invaild_message}{Color.reset()}"
            f"{Color.fg('gold')} in config: "
            f"{Color.fg('ruby')}{invaild_value} {Color.reset()}"
            f"{Color.fg('dove')}= {Color.reset()}"
            f"{Color.fg('ruby')}{type(invaild_value)}{Color.reset()}"
            f"{Color.fg('gold')} Try using "
            f"{Color.fg('red')}{correct_message} {Color.reset()}"
            f"{Color.fg('gold')}to continue ...{Color.reset()}"
        )

    # 1. duplicate 區段
    @staticmethod
    def _check_duplicate(config: dict) -> None:
        dup = config.get("duplicate")
        if not isinstance(dup, dict):
            raise TypeError("duplicate must be a dict")
        if not isinstance(dup.get("default"), bool):
            raise TypeError("duplicate.default must be boolean")
        overrides = dup.get("overrides", {})
        if not isinstance(overrides, dict):
            raise TypeError("duplicate.overrides must be a dict")
        for key in ("image", "video", "post", "notice"):
            val = overrides.get(key)
            if val is None:
                ConfigLoader.print_warning(key, val, "False")
                overrides[key] = False
            elif not isinstance(val, bool):
                raise TypeError(f"duplicate.overrides.{key} must be boolean")
        dup["overrides"] = overrides
        config["duplicate"] = dup

    # 2. headers.User-Agent
    @staticmethod
    def _check_headers(config: dict) -> None:
        headers = config.get("headers", {})
        if not isinstance(headers, dict):
            raise TypeError("headers must be a dict")
        ua = headers.get("User-Agent")
        fakeua = headers.get("Fake-User-Agent")
        if fakeua and not isinstance(fakeua, bool):
            headers["Fake-User-Agent"] = False
            raise TypeError("headers.Fake-User-Agent must be a bool")
        if not ua or not isinstance(ua, str):
            ConfigLoader.print_warning("User-Agent", ua, DEFAULT_UA)
            headers["User-Agent"] = DEFAULT_UA
        config["headers"] = headers

    # 3. output_template 區段
    @staticmethod
    def _check_output_template(config: dict) -> None:
        ot = config.get("output_template", {})
        if not isinstance(ot, dict):
            raise TypeError("output_template must be a dict")
        required_title_fields = [
            "video",
            "json_file_name",
            "html_file_name",
            "image_file_name",
            "playlist_file_name",
        ]
        for key in required_title_fields:
            val = ot.get(key)
            if not isinstance(val, str) or not val:
                raise ValueError(f"output_template.{key} must be a non-empty string")
            if "{title}" not in val:
                raise ValueError(f"output_template.{key} must include '{{title}}' as a placeholder")
        # tag
        tag = ot.get("tag")
        if not isinstance(tag, str):
            ConfigLoader.print_warning("output_template.tag", tag, "Empty-Tag")
            ot["tag"] = ""
        # date_formact
        date_fmt = ot.get("date_formact")
        if not isinstance(date_fmt, str) or not date_fmt:
            ConfigLoader.print_warning("output_template.date_formact", date_fmt, "%Y%m%d_%H%M%S")
            ot["date_formact"] = "%Y%m%d.%H%M%S"
        config["output_template"] = ot

    # 4. Donwload_Dir_Name 區段
    @staticmethod
    def _check_download_dir_name(config: dict) -> None:
        dld = config.get("donwload_dir_name", {})
        if not isinstance(dld, dict):
            raise TypeError("donwload_dir_name must be a dict")
        defaults = {
            "download_dir": "Berriz.Downloads",
            "dir_name": "{date} {community_name} {artist} {title}",
            "date_formact": "%y%m%d_%H-%M_%S",
        }
        for key, default_val in defaults.items():
            val = dld.get(key)
            if not isinstance(val, str) or not val:
                ConfigLoader.print_warning(f"donwload_dir_name.{key}", val, default_val)
                dld[key] = default_val
        config["donwload_dir_name"] = dld

    # 5. Container 區段
    @staticmethod
    def _check_container(config: dict) -> None:
        cont = config.get("Container", {})
        if not isinstance(cont, dict):
            raise TypeError("Container must be a dict")

        # Helper function for shaka-packager validation
        def _is_shaka_packager(value):
            """Check if value represents shaka-packager"""
            if not isinstance(value, str):
                return False
            normalized = value.lower()
            return set("shakapackager").issubset(set(normalized)) and ("shaka" in normalized or "packager" in normalized)

        # Field configurations
        CONTAINER_FIELDS = {
            "mux": {"default": "ffmpeg", "allowed": ["ffmpeg", "mkvtoolnix"]},
            "video": {
                "default": None,
                "allowed": ["ts", "mp4", "mov", "m4v", "mkv", "avi"],
                "required": True,
            },
            "decryption-engine": {
                "default": "SHAKA_PACKAGER",
                "allowed": None,  # Custom validation via normalize
            },
        }
        # Validate fields
        for field_name, config_rules in CONTAINER_FIELDS.items():
            value = cont.get(field_name)

            # Type check and default handling
            if not isinstance(value, str):
                if config_rules.get("required"):
                    raise ValueError(f"Container.{field_name} is required")
                ConfigLoader.print_warning(f"Container.{field_name}", value, config_rules["default"])
                cont[field_name] = config_rules["default"]
                continue
            # Special handling for decryption-engine
            if field_name == "decryption-engine":
                if _is_shaka_packager(value):
                    cont[field_name] = "SHAKA_PACKAGER"
                    # cont[field_name] = "mp4decrypt"
                continue
            # Validate against allowed values
            if config_rules["allowed"]:
                if value.lower() not in config_rules["allowed"]:
                    allowed_str = ", ".join(config_rules["allowed"])
                    raise ValueError(f"Container.{field_name} must be one of: {allowed_str}")

        tools = ["mp4decrypt", "shaka-packager", "mkvmerge"]
        for key in tools:
            if not isinstance(cont.get(key), str):
                raise TypeError(f"Tools setting '{key}' to be a string, got {type(cont.get(key)).__name__}")
        config["Container"] = cont

    # 6. Video 區段
    @staticmethod
    def _check_hls_dash(config: dict) -> tuple[str, str, str, str]:
        hls_sec = config.get("Video", {})
        if not isinstance(hls_sec, dict):
            raise TypeError("Video must be a dict")

        # Resolution normalization helper
        def _normalize_resolution(value, strip_suffixes):
            """Remove common resolution suffixes (p, i, k, kb, mb, etc.)"""
            if value is None:
                return None
            normalized = str(value).lower().strip()
            # Build regex pattern from suffixes list
            # Sort by length (longest first) to avoid partial matches
            sorted_suffixes = sorted(strip_suffixes, key=len, reverse=True)
            pattern = "|".join(re.escape(s) for s in sorted_suffixes)
            normalized = re.sub(f"(?i)({pattern})$", "", normalized)
            return normalized.strip()

        # Field configurations
        HLS_FIELDS = {
            "Video_Resolution_Choice": {
                "expected_type": (str, int),
                "default": "ask",
                "allowed": [
                    "144",
                    "256",
                    "360",
                    "640",
                    "480",
                    "854",
                    "720",
                    "1280",
                    "1080",
                    "1920",
                    "ask",
                    "none",
                ],
                "strip_suffixes": ["p", "i"],
            },
            "Audio_Resolution_Choice": {
                "expected_type": (str, int),
                "default": "ask",
                "allowed": ["192", "ask", "as", "none"],
                "strip_suffixes": ["kbs", "mbs", "kb", "mb", "k", "m", "g", "p", "i"],
            },
            "Video_codec": {
                "expected_type": str,
                "default": "h264",
                "allowed": [
                    "avc",
                    "avc1",
                    "h264",
                    "h.264",
                ],
            },
        }

        # Validate Video_codec first
        user_choice_video_codec = paramstore.get("vcodec")
        if user_choice_video_codec is not None:
            hls_sec["Video_codec"] = paramstore.get("vcodec")
        for codec_field in ["Video_codec"]:
            value = hls_sec.get(codec_field)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Video.{codec_field} must be a string")

        # Validate each field
        if paramstore.get("quality") is not None:
            hls_sec["Video_Resolution_Choice"] = paramstore.get("quality")
        if paramstore.get("noaudio") is True:
            hls_sec["Audio_Resolution_Choice"] = "none"
        if paramstore.get("novideo") is True:
            hls_sec["Video_Resolution_Choice"] = "none"

        for field_name, video_audio_config in HLS_FIELDS.items():
            value = hls_sec.get(field_name)
            # Type validation and default assignment
            if not isinstance(value, video_audio_config["expected_type"]):
                warning = video_audio_config.get("warning", video_audio_config["default"])
                ConfigLoader.print_warning(f"Video.{field_name}", value, warning)
                hls_sec[field_name] = video_audio_config["default"]
                continue
            # Resolution normalization and validation
            if "strip_suffixes" in video_audio_config:
                normalized = _normalize_resolution(value, video_audio_config["strip_suffixes"])
                if normalized not in video_audio_config["allowed"]:
                    ConfigLoader.print_warning(field_name, value, video_audio_config["default"])
                    hls_sec[field_name] = video_audio_config["default"]
                else:
                    hls_sec[field_name] = normalized
            # Codec validation (for Video_codec)
            elif field_name in ["Video_codec"]:
                if value is not None and isinstance(value, str):
                    normalized = value.lower().strip()
                    if normalized not in video_audio_config["allowed"]:
                        ConfigLoader.print_warning(field_name, value, video_audio_config["default"])
                        hls_sec[field_name] = video_audio_config["default"]
                    else:
                        hls_sec[field_name] = normalized

        # Cross-validation: ensure at least one resolution is set
        video_res = hls_sec.get("Video_Resolution_Choice")
        audio_res = hls_sec.get("Audio_Resolution_Choice")
        if video_res == "none" and audio_res == "none":
            raise ValueError("Video: Video_Resolution_Choice and Audio_Resolution_Choice cannot both be 'none'")
        video_codec = hls_sec.get("Video_codec")
        config["Video"] = hls_sec
        if any(isinstance(res, str) for res in [video_res, audio_res, video_codec]):
            return video_res, audio_res, video_codec

    # 7. TimeZone 區段
    @staticmethod
    def _check_timezone(config: dict) -> None:
        tz = config.get("TimeZone", {})
        if not isinstance(tz, dict):
            raise TypeError("TimeZone must be a dict")
        time_str = tz.get("time")
        if not isinstance(time_str, (int, str)):
            raise ValueError("TimeZone.time must be a string or int")
        if isinstance(time_str, str):
            int_brisbane_offset = int(re.sub(r"(?i)|utc", "", time_str).strip().lower())
            if not (-12 <= int_brisbane_offset <= 14):
                ConfigLoader.print_warning(
                    "TimeZone invaild should be -12 ~ +14",
                    int_brisbane_offset,
                    "UTC +9",
                )
                tz["TimeZone"] = 9
        config["TimeZone"] = tz

    # 8. KeyService 區段
    @staticmethod
    def _check_keyservice(config: dict) -> None:
        ks = config.get("KeyService", {})
        if not isinstance(ks, dict):
            raise TypeError("KeyService must be a dict")

        source = ks.get("source")
        if not isinstance(source, str):
            raise ValueError("KeyService.source must be a string")
        valid_sources = {
            "playready",
            "widevine",
            "remote_widevine",
            "remote_playready",
            "watora",
            "http_api",
            "none",
        }
        source_lower = source.lower()
        if source_lower not in valid_sources:
            raise ValueError(f"KeyService.source must be one of: {valid_sources}")
        else:
            ks["KeyService"] = source_lower
        config["KeyService"] = ks

    @staticmethod
    def is_valid_url(u):
        return all([urlparse(u).scheme, urlparse(u).netloc])

    # 8-1 remote_cdm
    @staticmethod
    def check_remote_cdm(config: dict) -> None:
        """Check if remote_cdm is set in config"""
        test = []
        remote_tuple = ("playready", "widevine", "http_api")
        remote_cdm = config.get("remote_cdm", {})
        for cdm_config in remote_cdm:
            test.append(cdm_config.get("name"))
            if cdm_config.get("name", {}) not in remote_tuple:
                raise ValueError("remote_cdm.name must be one of: playready, widevine, http_api")
            if cdm_config.get("security_level", {}):
                if not isinstance(int(cdm_config.get("security_level")), int):
                    raise ValueError("remote_cdm.security_level must be an integer")
            if cdm_config.get("host", {}):
                if not isinstance(cdm_config.get("host"), str):
                    raise ValueError("remote_cdm.url must be a string")
                if ConfigLoader.is_valid_url(cdm_config.get("host")) is False:
                    raise ValueError("remote_cdm.url must be a valid url")
        if not all(item in remote_tuple for item in test):
            raise ValueError(f"remote_cdm must of: {remote_tuple}")

    # 9. CDM 區
    @staticmethod
    def _check_cdm(config: dict) -> None:
        cdm = config.get("CDM", {})
        if not isinstance(cdm, dict):
            raise TypeError("CDM must be a dict")

        CDM_FIELDS = {
            "widevine": {"extension": ".wvd", "path_attr": "wv_device_path"},
            "playready": {"extension": ".prd", "path_attr": "prd_device_path"},
        }

        for field_name, field_config in CDM_FIELDS.items():
            value = cdm.get(field_name)
            if value is None:
                continue

            if not isinstance(value, str):
                raise ValueError(f"CDM.{field_name} must be a string")

            cdm_path = CDM_PATH({"CDM": cdm})
            actual_path = Path(getattr(cdm_path, field_config["path_attr"]))

            if not actual_path.exists():
                # 在同資料夾下搜尋副檔名大小寫不同的檔案
                folder = actual_path.parent
                stem = actual_path.stem
                matches = [p for p in folder.glob(f"{stem}.*") if p.suffix.lower() == field_config["extension"].lower()]

                if matches:
                    actual_path = matches[0]
                else:
                    raise ValueError(f"CDM.{field_name} not found: {actual_path} (case-insensitive search also failed)")

            logger.info(f"Load CDM: {Color.fg('dark_gray')}{actual_path.parent}　\n{Color.reset()}{Color.fg('green')} ⤷ {Color.fg('dark_yellow')}{actual_path.name}{Color.reset()}")

        config["CDM"] = cdm

    @staticmethod
    def _check_berriz(config: dict) -> None:
        user = config.get("berriz", {})
        if not isinstance(user, dict):
            raise TypeError("berriz must be a dict")

        accounts = user.get("account", [])
        if not isinstance(accounts, list):
            raise TypeError("berriz.account must be a list")

        validated_accounts = []
        for entry in accounts:
            if not isinstance(entry, str):
                raise ValueError("Each berriz.account entry must be a string in 'email:password' format")
            if ":" not in entry:
                raise ValueError("Each berriz.account entry must contain ':' separating email and password")

            email, password = entry.split(":", 1)
            if not isinstance(email, str) or not isinstance(password, str):
                raise ValueError("Email and password must be strings")
            if not check_email(email):
                raise ValueError(f"Invalid email format in berriz.account: {email}")

            validated_accounts.append({"email": email, "password": password})

        config["berriz"] = {"account": validated_accounts}

    # 11. logging 區段
    @staticmethod
    def _check_logging(config: dict) -> None:
        log = config.get("logging", {})
        if not isinstance(log, dict):
            raise TypeError("logging must be a dict")

        # Configuration for logging fields
        LOGGING_FIELDS = {
            "level": {
                "allowed_values": ["debug", "info", "warning", "error", "critical"],
                "case_sensitive": False,
            },
            "format": {"allowed_values": None},  # No restriction on format string
        }
        # Validate logging fields
        for field_name, field_config in LOGGING_FIELDS.items():
            value = log.get(field_name)
            # Type validation
            if not isinstance(value, str):
                raise ValueError(f"logging.{field_name} must be a string")
            # Value validation if allowed_values is specified
            if field_config["allowed_values"]:
                check_value = value.lower() if not field_config.get("case_sensitive") else value

                if check_value not in field_config["allowed_values"]:
                    allowed_str = ", ".join(field_config["allowed_values"])
                    raise ValueError(f"logging.{field_name} must be one of: {allowed_str}")
        config["logging"] = log

    # 12. Proxy 區段
    @staticmethod
    def _check_proxy(config: dict) -> None:
        proxy = config.get("Proxy", {})
        if not isinstance(proxy, dict):
            raise TypeError("Proxy must be a dict")
        if not isinstance(proxy.get("http"), list):
            raise TypeError("Proxy.http must be a list")
        if not isinstance(proxy.get("https"), list):
            raise TypeError("Proxy.https must be a list")
        # Configuration for proxy boolean fields
        PROXY_BOOL_FIELDS = {
            "Proxy_Enable": {"default": False},
            "use_proxy_list": {"default": False},
        }
        # Validate proxy boolean fields
        for field_name, field_config in PROXY_BOOL_FIELDS.items():
            value = proxy.get(field_name)
            if not isinstance(value, bool):
                ConfigLoader.print_warning(f"Proxy.{field_name}", value, str(field_config["default"]))
                proxy[field_name] = field_config["default"]
        config["Proxy"] = proxy

    # 13. Setting
    @staticmethod
    def _check_setting(config: dict) -> None:
        setting = config.get("Setting", {})
        if not isinstance(setting, dict):
            raise TypeError("Setting must be a dict")

        # 原始鍵名與目標paramstore._store的名字
        setting_map = {
            "nocookie": "no_cookie",
            "skip-download": "nodl",
            "skip-json": "nojson",
            "skip-thumbnails": "nothumbnails",
            "skip-playlist": "notplaylist",
            "skip-html": "nohtml",
            "no-subfolder": "nosubfolder",
        }
        for setting_key, store_key in setting_map.items():
            value = setting.get(setting_key)
            if not isinstance(value, bool):
                raise ValueError(f"Setting.{setting_key} must be a boolean")
            if value:
                paramstore._store[store_key] = True  # 若值為 True，則寫入 paramstore

    @staticmethod
    def _berrizapiclient(config: dict[str, Any]) -> None:
        should_int: tuple[str, ...] = (
            "max_retries",
            "connector_limit",
            "connector_limit_per_host",
            "keepalive_timeout",
            "ttl_dns_cache",
            "timeouttotal",
            "timeeoutconnect",
            "timeoutsock_connect",
            "timeeoutsock_read",
        )
        should_bool: tuple[str, ...] = (
            "show_log",
            "enable_cleanup_closed",
            "force_close",
            "use_dns_cache",
        )
        should_float: tuple[str, ...] = ("base_sleep", "max_sleep")

        berriz = config.get("BerrizAPIClient", {})

        if not isinstance(berriz, dict):
            raise ValueError("BerrizAPIClient must be a dict")

        allowed_keys: set[str] = set(should_int) | set(should_bool) | set(should_float)

        extra_keys = [k for k in berriz.keys() if k not in allowed_keys]
        if extra_keys:
            raise ValueError(f"Unexpected keys in BerrizAPIClient: {extra_keys}")

        errors: list[str] = []
        for k, v in berriz.items():
            if k in should_int:
                # bool is subclass of int; explicitly reject bool
                if not isinstance(v, int) or isinstance(v, bool):
                    errors.append(f"'{k}' should be int (got {type(v).__name__})")
            elif k in should_bool:
                if not isinstance(v, bool):
                    errors.append(f"'{k}' should be bool (got {type(v).__name__})")
            elif k in should_float:
                # accept float or int
                if not (isinstance(v, float) or (isinstance(v, int) and not isinstance(v, bool))):
                    errors.append(f"'{k}' should be float (got {type(v).__name__})")

        if errors:
            raise ValueError("Type errors in BerrizAPIClient: " + "; ".join(errors))

    @staticmethod
    def _video_download(config: dict[str, Any]) -> None:
        should_int: tuple[str, ...] = (
            "connector_limit",
            "connector_limit_per_host",
            "connector_keepalive_timeout",
            "connector_enable_cleanup_closed",
            "timeout_total",
            "timeout_connect",
            "timeout_sock_read",
            "timeout_sock_connect",
            "max_retries",
            "semaphore",
            "connector_ttl_dns_cache",
        )
        should_bool: tuple[str, ...] = ("connector_use_dns_cache",)
        should_float: tuple[str, ...] = ()

        video = config.get("VideoDownload", {})

        if not isinstance(video, dict):
            raise ValueError("VideoDownload must be a dict")

        allowed_keys: set[str] = set(should_int) | set(should_bool) | set(should_float)

        extra = [k for k in video.keys() if k not in allowed_keys]
        if extra:
            raise ValueError(f"Unexpected keys in VideoDownload: {extra}")

        errors: list[str] = []
        for k, v in video.items():
            if k in should_int:
                # reject bool because bool is subclass of int
                if not isinstance(v, int) or isinstance(v, bool):
                    errors.append(f"'{k}' should be int (got {type(v).__name__})")
            elif k in should_bool:
                if not isinstance(v, bool):
                    errors.append(f"'{k}' should be bool (got {type(v).__name__})")
            elif k in should_float:
                if not (isinstance(v, float) or (isinstance(v, int) and not isinstance(v, bool))):
                    errors.append(f"'{k}' should be float (got {type(v).__name__})")

        if errors:
            raise ValueError("Type errors in VideoDownload: " + "; ".join(errors))

        return None

    @staticmethod
    def check_cfg(config: dict) -> None:
        """驗證並填充 config 各區段的預設值"""
        if not isinstance(config, dict):
            raise TypeError("Config must be a dictionary")

        # 1 duplicate 區段
        ConfigLoader._check_duplicate(config)

        # 2 headers.User-Agent
        ConfigLoader._check_headers(config)

        # 3 output_template 區段
        ConfigLoader._check_output_template(config)

        # 4 Donwload_Dir_Name 區段
        ConfigLoader._check_download_dir_name(config)

        # 5 Container 區段
        ConfigLoader._check_container(config)

        # 6 Video 區段
        # 移動到Download初始化
        # ConfigLoader._check_hls_dash(config)

        # 7 TimeZone 區段
        ConfigLoader._check_timezone(config)

        # 8 KeyService 區段
        ConfigLoader._check_keyservice(config)

        # 8-1 remote_cdm
        ConfigLoader.check_remote_cdm(config)

        # 9 CDM 區段
        ConfigLoader._check_cdm(config)

        # 10 berriz 區段
        ConfigLoader._check_berriz(config)

        # 11 logging 區段
        ConfigLoader._check_logging(config)

        # 12 Proxy 區段
        ConfigLoader._check_proxy(config)

        # 13 Setting
        ConfigLoader._check_setting(config)

        # 14 berrizapiclient
        ConfigLoader._berrizapiclient(config)

        # 15 VideoDownload
        ConfigLoader._video_download(config)


CFG = ConfigLoader.load()


# By edit tools {} remove or add tools to bypass tools_check()
def tools_check() -> None:
    R = Route()
    tools = {
        "mp4decrypt": R.mp4decrypt_path,
        "packager": R.packager_path,
        "mkvmerge": R.mkvmerge_path,
        "ffmpeg": R.ffmpeg,
    }
    if _check_tool_version(["mkvmerge", "--version"]):
        # 版本檢查成功，不再需要檢查路徑
        paramstore._store["mkvmerge_path_ok"] = True
        tools.pop("mkvmerge", None)
    if CFG["Container"]["mux"] == "mkvtoolnix":
        tools.pop("ffmpeg", None)
    elif CFG["Container"]["mux"] == "ffmpeg":
        tools.pop("mkvmerge", None)
    if _check_tool_version(["ffmpeg", "-version"]):
        # 版本檢查成功，不再需要檢查路徑
        paramstore._store["ffmpeg_path_ok"] = True
        tools.pop("ffmpeg", None)
    if _check_tool_version(["packager", "--version"]):
        # 版本檢查成功，不再需要檢查路徑
        paramstore._store["packager_path_ok"] = True
        tools.pop("packager", None)
    if CFG["Container"]["decryption-engine"] == "mp4decrypt":
        tools.pop("packager", None)
    elif CFG["Container"]["decryption-engine"] == "SHAKA_PACKAGER":
        tools.pop("mp4decrypt", None)

    missing = {name: path for name, path in tools.items() if not os.path.exists(path)}

    if missing:
        # 確保在報錯時版本檢查失敗但存在於路徑中的工具也會被列出
        msg = f"Missing tools:{Color.fg('gold')} " + " & ".join(f"{name} ({path})" for name, path in missing.items())
        logger.error(msg)
        for key, path in missing.items():
            check: str = f"{Color.fg('gold')}Check website to download {Color.fg('cyan')}"
            end: str = Color.reset()
            if key == "mp4decrypt":
                print(check, "https://www.bento4.com/downloads/", end)
            if key == "packager":
                for p in Path(path.parent).rglob("*"):
                    if ("shaka" in p.name) or ("packager" in p.name):
                        logger.info(f"Try rename {Color.fg('ruby')}{p.name}{Color.fg('light_gray')} to{Color.fg('gold')} packager.exe{Color.fg('light_gray')} at {Color.fg('platinum')}{p}{Color.reset()}")
                print(
                    check,
                    "https://github.com/shaka-project/shaka-packager/releases/latest",
                    end,
                )
            if key == "mkvmerge":
                print(check, "https://mkvtoolnix.org/", end)
            if key == "ffmpeg":
                print(check, "https://www.ffmpeg.org/download.html", end)
        raise FileNotFoundError(f"Required tools {', '.join(missing)} not found exit.")


try:
    tools_check()
except FileNotFoundError as e:
    logger.info(e)
    sys.exit(1)
