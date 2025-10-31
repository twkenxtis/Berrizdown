from key.cdm_path import CDM_PATH
from key.http_vault import HTTP_API
from key.remotecdm_pr import Remotecdm_Playready
from key.remotecdm_wv import Remotecdm_Widevine
from key.watora import Watora_wv
from lib.load_yaml_config import CFG
from lib.path import Path
from readydl_pyplayready.playready import PlayReadyDRM
from static.color import Color
from static.parameter import paramstore
from unit.handle.handle_log import setup_logging
from wvd.widevine import WidevineDRM

logger = setup_logging("GetClearKey", "honeydew")


DRM_Client = PlayReadyDRM | WidevineDRM


cdm_path = CDM_PATH(CFG)


async def get_clear_key(wv_pssh: str, pr_pssh: str, acquirelicenseassertion_input: str, drm_type: str) -> list[str] | None:
    prd_device_path: Path | str = cdm_path.prd_device_path or ""
    wv_device_path: Path | str = cdm_path.wv_device_path or ""
    exists, overwrite_cdm_path = check_cdm_path()
    if exists is True:
        suffix = Path(overwrite_cdm_path.name).suffix.lower()
        match suffix:
            case ".prd":
                drm_type = "playready"
                prd_device_path = Path(overwrite_cdm_path)
                pssh_input: str = pr_pssh
            case ".wvd":
                drm_type = "widevine"
                wv_device_path = Path(overwrite_cdm_path)
                pssh_input: str = wv_pssh
            case _:
                logger.error(f"Unsupported cdm file type: {suffix}, {overwrite_cdm_path}")
                return None

    if drm_type == "none":
        logger.info(f"{Color.bg('cobalt')}{Color.fg('rose')}User choose not use DRM, skip drm key{Color.reset()}")
        return None
    if drm_type == "remote_playready":
        if test_setting("playready") is False:
            return None
        pssh_input: str = pr_pssh
    if drm_type == "playready":
        prd_path_obj = Path(overwrite_cdm_path)
        final_path = prd_path_obj if prd_path_obj.exists() else prd_path_obj.with_name(prd_path_obj.name + ".prd")
        if not final_path.exists():
            logger.warning(f"PlayReady CDM file not found: {final_path}")
            return None
        prd_device_path = str(final_path)
    if drm_type == "remote_widevine":
        if test_setting("widevine") is False:
            return None
        pssh_input: str = wv_pssh
    if drm_type == "watora":
        if test_setting("widevine") is False:
            return None
        pssh_input: str = wv_pssh
    if drm_type == "widevine":
        original_path_obj = Path(wv_device_path)

        final_wv_path_obj = original_path_obj if original_path_obj.exists() else original_path_obj.with_name(original_path_obj.name + ".wvd")

        if not final_wv_path_obj.exists():
            logger.warning(f"Widevine CDM file not found. Neither the original path nor the .wvd fallback exists: {str(final_wv_path_obj)}")
            return None

        wv_device_path = str(final_wv_path_obj)
        pssh_input: str = wv_pssh
    if drm_type == "http_api":
        if test_setting("widevine") is False:
            return None
        pssh_input: tuple[str, str] = (wv_pssh, pr_pssh)

    drm: DRM_Client = drm_choese(drm_type, prd_device_path, wv_device_path)

    logger.info(
        f"{Color.fg('light_gray')}use {Color.fg('plum')}{drm_type}{Color.reset()} "
        f"{Color.fg('light_gray')}to get clear key{Color.reset()} "
        f"{Color.fg('light_gray')}assertion:{Color.reset()} "
        f"{Color.fg('dark_green')}{acquirelicenseassertion_input}{Color.reset()}"
    )
    try:
        key: list[str] | None = await drm.get_license_key(pssh_input, acquirelicenseassertion_input)
        if key:
            logger.info(f"Request new key: {Color.fg('khaki')}kid:{Color.fg('gold')}{key[0].split(':')[0]} {Color.fg('bright_red')}key:{Color.fg('gold')}{key[0].split(':')[1]}{Color.reset()}")
            return key
        logger.error("Failed to retrieve license key")
        return None
    except Exception as e:
        logger.error(f"Exception while retrieving license key: {e}")
        raise  # 重新拋出異常
    finally:
        if drm:
            try:
                drm.close()
            except Exception:
                pass


def drm_choese(drm_type: str, prd_device_path=None, wv_device_path=None) -> DRM_Client:
    drm: DRM_Client
    if drm_type == "playready":
        if prd_device_path is not None:
            drm = PlayReadyDRM(prd_device_path)
    elif drm_type == "widevine":
        if wv_device_path is not None:
            drm = WidevineDRM(wv_device_path)
    elif drm_type == "remote_widevine":
        drm = Remotecdm_Widevine()
    elif drm_type == "remote_playready":
        drm = Remotecdm_Playready()
    elif drm_type == "watora":
        drm = Watora_wv()
    elif drm_type == "http_api":
        drm = HTTP_API()
    else:
        drm = WidevineDRM(wv_device_path)
    return drm


def test_setting(type: str) -> bool:
    SUPPORTED_CDM = {"playready", "widevine"}
    name_lower = type.lower()
    if name_lower not in SUPPORTED_CDM:
        logger.error(f"Unsupported CDM type: {type}")
        return False

    for setting in CFG.get("remote_cdm", []):
        if setting.get("name", "").lower() == name_lower:
            if any(v is None for v in setting.values()):
                missing = [k for k, v in setting.items() if v is None]
                logger.error(f"Fail to get {missing} from config file for remote CDM")
                logger.info(f"Remote cdm setting: {setting}")
                return False

            return True

    logger.error(f"No CDM setting found for type {type}")
    return False


def check_cdm_path() -> tuple[bool, Path]:
    overwrite_cdm: Path = Path("")
    if paramstore.get("cdm"):
        overwrite_cdm: Path = Path(paramstore.get("cdm"))
        if overwrite_cdm.exists():
            return True, Path(overwrite_cdm)
        else:
            logger.error(f"CDM path {overwrite_cdm} not exists")
            raise FileNotFoundError(f"CDM path {overwrite_cdm} not exists")
    return False, Path(overwrite_cdm)
