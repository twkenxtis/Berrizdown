import difflib
import re
import sys
from typing import Any

import click

from berrizdown.lib.urlextra import URLExtractor
from berrizdown.static.color import Color
from berrizdown.unit.handle.handle_log import setup_logging


logger = setup_logging("click_types", "mint")


# 全域儲存參數
_global_args: dict[str, Any] = {}


# 已知旗標列表
known_flags: list[str] = [
    "-k",
    "--key",
    "--keys",
    "--help",
    "--h",
    "-h",
    "-H",
    "-?",
    "--?",
    "--no_cookie",
    "--nocookie",
    "--no-cookie",
    "-nc",
    "--join",
    "--join-community",
    "--join_community",
    "--leave",
    "--leave-community",
    "--leave_community",
    "--fanclub-only",
    "--fanclub",
    "--fc",
    "--no-fanclub",
    "-nfc",
    "--live",
    "--live-only",
    "-l",
    "--media",
    "--media-only",
    "-m",
    "--t--T",
    "--tt--TT",
    "--community",
    "-cm",
    "--change-password",
    "--change_password",
    "--del-after-done",
    "--skip-merge",
    "--board",
    "-b",
    "--photo",
    "--photo-only",
    "--notice",
    "--notice-only",
    "-n",
    "-g",
    "--group",
    "--skip-mux",
    "--signup",
    "--skip-dl",
    "--skip-download",
    "--skip-json",
    "--skip-thumbnails",
    "--skip-thb",
    "--skip-playlist",
    "--skip-pl",
    "--skip-html",
    "--no-info",
    "--noinfo",
    "--skip-videos",
    "--skip-v",
    "--skip-video",
    "--skipvideo",
    "--nosubfolder",
    "--no-subfolder",
    "--no_subfolder",
    "--skip-images",
    "--skip-imgs",
    "--skip-img",
    "--skip-image",
    "-q",
    "--quality",
    "-v",
    "--vcodec",
    "-a",
    "--acodec",
    "-na",
    "--no-audio"
    "-nv",
    "--no-video",
    "--skip-audio",
    "--skip-a",
    "--skipaudio",
    "--ss",
    "--to",
    "--list",
    "--retitle",
    "--cdm",
    "--cache",
    "--no-cache",
    "-c",
    "--cmt",
    "--artisid",
    "--v",
    "--version",
    "--save-dir",
    "--subs-only",
    "-ns",
    "--no-subs"
]


def suggest_unknown_args(unknown: list[str], known_flags: list[str]) -> None:
    """提示未識別參數的可能拼寫建議"""
    for u in unknown:
        suggestion = difflib.get_close_matches(u, known_flags, n=1, cutoff=0.5)
        if suggestion:
            logger.info(f"{Color.fg('light_gray')}You probably meant {Color.fg('gold')}{suggestion[0]} {Color.reset()}instead of {Color.fg('light_gray')}{u}{Color.reset()}")
            logger.error(f"{Color.bg('sunflower')}Unrecognized parameter:{Color.bold()}{Color.bg('tungsten')} {u}{Color.reset()}")
            raise ValueError("Invaild args error exit")


def _get_arg(key: str, default: Any = None) -> Any:
    """獲取參數值的輔助函數"""
    if _global_args:
        return _global_args.get(key, default)

    try:
        ctx = click.get_current_context(silent=True)
        if ctx and ctx.obj:
            return ctx.obj.get(key, default)
    except RuntimeError:
        pass

    return default


def apply_no_info(ctx, param, value):
    if value:
        ctx.params["nojson"] = True
        ctx.params["nothumbnails"] = True
        ctx.params["notplaylist"] = True
        ctx.params["nohtml"] = True


@click.command(
    add_help_option=False,  # 禁用 Click 的預設 help
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=True),
)
@click.option("-k", "--key", "--keys", "has_key", is_flag=True, help="Show key and skip download")
@click.option(
    "--help",
    "--h",
    "-h",
    "-H",
    "-?",
    "--?",
    "show_help",
    is_flag=True,
    help="Show help",
)
@click.option(
    "--no-cookie",
    "--no_cookie",
    "--nocookie",
    "-nc",
    "had_nocookie",
    is_flag=True,
    help="No cookie use",
)
@click.option(
    "--join",
    "--join-community",
    "--join_community",
    "join_community",
    default="",
    help="Join a community",
)
@click.option(
    "--leave",
    "--leave-community",
    "--leave_community",
    "leave_community",
    default="",
    help="Leave a community",
)
@click.option(
    "--fanclub-only",
    "--fanclub",
    "-fc",
    "fanclub",
    is_flag=True,
    help="Show only fanclub-only content",
)
@click.option(
    "--no-fanclub",
    "-nfc",
    "nofanclub",
    is_flag=True,
    help="Show only non-fanclub-only content",
)
@click.option(
    "--live",
    "--live-only",
    "-l",
    "liveonly",
    is_flag=True,
    help="Show only live content",
)
@click.option(
    "--media",
    "--media-only",
    "-m",
    "mediaonly",
    is_flag=True,
    help="Show only media content",
)
@click.option(
    "--t",
    "--T",
    "time_date1",
    type=str,
    nargs=1,
    help="Filter content by date/time (use 1-2 times)",
)
@click.option(
    "--tt",
    "--TT",
    "time_date2",
    type=str,
    nargs=1,
    help="Filter content by date/time (use 1-2 times)",
)
@click.option("--community", "-cm", is_flag=True, help="Show community content")
@click.option(
    "--change-password",
    "--changepassword",
    "change_password",
    is_flag=True,
    help="Change password",
)
@click.option("--signup", is_flag=True, help="Signup")
@click.option(
    "--del-after-done",
    "clean_dl",
    type=click.BOOL,
    default=None,
    help="Delete after completion",
)
@click.option("--skip-merge", "skip_merge", is_flag=True, help="Skip merge after completion")
@click.option("--skip-mux", "skip_mux", is_flag=True, help="Skip mux after merge")
@click.option("--board", "-b", is_flag=True, help="Choose board")
@click.option("--photo", "--photo-only", "-p", "photoonly", is_flag=True, help="Choose photo")
@click.option("--notice", "--notice-only", "-n", "noticeonly", is_flag=True, help="Choose notice")
@click.option("--group", "-g", "group", default="default_group", help="Group name (Default: ive)")
@click.option("--skip-dl", "--skip-download", "nodl", is_flag=True, help="No download")
@click.option(
    "--skip-json",
    "--skip-Json",
    "--skip-JSON",
    "--skipjson",
    "nojson",
    is_flag=True,
    help="No Json downloadDisable)",
)
@click.option(
    "--skip-thumbnails",
    "--skip-thb",
    "nothumbnails",
    is_flag=True,
    help="No thumbnails download",
)
@click.option(
    "--skip-playlist",
    "--skip-pl",
    "--skip-Playlist",
    "--skipplaylist",
    "notplaylist",
    is_flag=True,
    help="No playlist download",
)
@click.option(
    "--skip-html",
    "--skip-Html",
    "--skip-HTML",
    "--skiphtml",
    "nohtml",
    is_flag=True,
    help="No html download",
)
@click.option(
    "-nv",
    "-vn",
    "--no-video",
    "--skip-videos",
    "--skip-v",
    "--skip-video",
    "--skipvideo",
    "novideo",
    is_flag=True,
    help="No video download",
)
@click.option(
    "--no-info",
    "--noinfo",
    "no_info",
    is_flag=True,
    expose_value=True,
    callback=apply_no_info,
    help="Skip all info-related downloads (json, thumbnails, playlist, html)",
)
@click.option(
    "--nosubfolder",
    "--no-subfolder",
    "--no_subfolder",
    "nosubfolder",
    is_flag=True,
    help="No SUB Folder",
)
@click.option(
    "--skip-images",
    "--skip-imgs",
    "--skip-img",
    "--skip-image",
    "--skipimage",
    "noimages",
    is_flag=True,
    help="No images",
)
@click.option(
    "-q",
    "--quality",
    "quality",
    help="Quality",
)
@click.option(
    "-v",
    "--vcodec",
    "vcodec",
    default="h264",
    help="Video Codec",
)
@click.option(
    "-na",
    "-an",
    "--no-audio",
    "--skip-audio",
    "--skip-a",
    "--skipaudio",
    "noaudio",
    is_flag=True,
    help="No audio",
)
@click.option(
    "-S",
    "--subs-only",
    "subs_only",
    is_flag=True,
    help="subs only",
)
@click.option(
    "-ns",
    "--no-subs",
    "no_subs",
    is_flag=True,
    help="no subs",
)
@click.option(
    "--ss",
    "start_time",
    type=str,
    help="Start time (seconds, must be int or float)",
)
@click.option(
    "--to",
    "end_time",
    type=str,
    help="End time (seconds, must be int or float)",
)
@click.option(
    "--list",
    "get_v_list",
    is_flag=True,
    help="Skip downloading and list available tracks and what tracks would have been downloaded.",
)
@click.option(
    "--retitle",
    "retitle",
    type=str,
    help="regular title",
)
@click.option(
    "--cdm",
    "cdm",
    type=str,
    help="Overwrite cdm",
)
@click.option(
    "--cache",
    "cache_key",
    is_flag=True,
    help="Disable CDM use and only retrieve decryption keys from Key Vaults",
)
@click.option(
    "--no-cache",
    "no_cache_key",
    is_flag=True,
    help="Disable Key Vaults use and only retrieve decryption keys from CDM",
)
@click.option(
    "-version",
    "--v",
    "--version",
    "version",
    is_flag=True,
    help="Version",
)
@click.option(
    "-c",
    "--cmt",
    "cmtonly",
    is_flag=True,
    help="Show comment or not",
)
@click.option(
    "--artisid",
    "artisid",
    type=str,
    multiple=True,
    help="Filter by artis id",
)
@click.option(
    "--save-dir",
    "savedir",
    type=str,
    multiple=False,
    help="Save directory path",
)
@click.argument("unknown", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def main(
    ctx: click.Context,
    has_key: bool,
    show_help: bool,
    had_nocookie: bool,
    join_community: str,
    leave_community: str,
    fanclub: bool,
    nofanclub: bool,
    liveonly: bool,
    mediaonly: bool,
    time_date1: str,
    time_date2: str,
    community: bool,
    change_password: bool,
    signup: bool,
    clean_dl: bool | None,
    skip_merge: bool,
    skip_mux: bool,
    board: bool,
    photoonly: bool,
    noticeonly: bool,
    group: str,
    nodl: bool,
    nojson: bool,
    nothumbnails: bool,
    notplaylist: bool,
    nohtml: bool,
    no_info: bool,
    nosubfolder: bool,
    noimages: bool,
    quality: str,
    vcodec: str,
    novideo: bool,
    noaudio: bool,
    start_time: str,
    end_time: str,
    get_v_list: bool,
    retitle: str,
    cdm: str,
    cache_key: bool,
    no_cache_key: bool,
    cmtonly: bool,
    artisid: str|list,
    version: bool,
    savedir: str,
    subs_only: bool,
    no_subs: bool,
    unknown: tuple,
) -> None:
    """
    Berriz DRM - Download and manage DRM content

    A comprehensive CLI tool for managing content with various filtering options.
    """
    global _global_args

    # 儲存所有參數
    args_dict = {
        "has_key": has_key,
        "show_help": show_help,
        "had_nocookie": had_nocookie,
        "join_community": join_community,
        "leave_community": leave_community,
        "fanclub": fanclub,
        "nofanclub": nofanclub,
        "liveonly": liveonly,
        "mediaonly": mediaonly,
        "time_date1": time_date1,
        "time_date2": time_date2,
        "community": community,
        "change_password": change_password,
        "signup": signup,
        "clean_dl": clean_dl,
        "skip_merge": skip_merge,
        "skip_mux": skip_mux,
        "board": board,
        "photoonly": photoonly,
        "noticeonly": noticeonly,
        "group": group,
        "nodl": nodl,
        "nojson": nojson,
        "notplaylist": notplaylist,
        "nothumbnails": nothumbnails,
        "nohtml": nohtml,
        "nosubfolder": nosubfolder,
        "no_info": no_info,
        "quality": quality,
        "vcodec": vcodec,
        "noaudio": noaudio,
        "novideo": novideo,
        "noimages": noimages,
        "start_time": start_time,
        "end_time": end_time,
        "get_v_list": get_v_list,
        "retitle": retitle,
        "cdm": cdm,
        "cache_key": cache_key,
        "no_cache_key": no_cache_key,
        "cmtonly": cmtonly,
        "artisid": artisid,
        "savedir": savedir,
        "version": version,
        "subs_only": subs_only,
        "no_subs": no_subs,
    }
    ctx.obj = args_dict
    _global_args = args_dict
    urls: tuple[str, ...] = URLExtractor()(unknown)
    urlset = set(urls)
    unknown_list = list(unknown)
    if urls != ():
        pattern: re.Pattern = re.compile("|".join(re.escape(v) for v in urlset))
        filtered = [s for s in unknown_list if not pattern.search(s)]
    else:
        filtered: list = unknown_list
    if filtered:
        logger.warning(f"Unknown args: {filtered}")
        suggest_unknown_args(filtered, known_flags)
        raise ValueError("Invalid args error exit")
    
    logger.info(f"{Color.fg('mint')}Arguments parsed successfully{Color.reset()}")

    from berrizdown.static.parameter import paramstore
    
    if version:
        from static.version import __version__
        logger.info(f"{Color.fg('aquamarine')}Berrizdown version: {Color.fg('gold')}{__version__}{Color.reset()}")

    if urls:
        paramstore._store["click_urls"] = urls
    
    if has_key:
        paramstore._store["key"] = True

    if had_nocookie:
        paramstore._store["no_cookie"] = True

    if clean_dl is False:
        paramstore._store["clean_dl"] = False
    elif clean_dl is None:
        paramstore._store["clean_dl"] = True
    else:
        paramstore._store["clean_dl"] = clean_dl

    if skip_merge:
        paramstore._store["skip_merge"] = True

    if skip_mux:
        paramstore._store["skip_mux"] = True

    if fanclub:
        paramstore._store["fanclub"] = True

    if nofanclub:
        paramstore._store["fanclub"] = False

    if nofanclub:
        paramstore._store["fanclub"] = False

    if nodl:
        paramstore._store["nodl"] = True
    
    if nojson:
        paramstore._store["nojson"] = True

    if nothumbnails:
        paramstore._store["nothumbnails"] = True

    if notplaylist:
        paramstore._store["noplaylist"] = True

    if nohtml:
        paramstore._store["nohtml"] = True

    if nosubfolder:
        paramstore._store["nosubfolder"] = True

    if noimages:
        paramstore._store["noimages"] = True

    if novideo:
        paramstore._store["novideo"] = True

    if quality:
        paramstore._store["quality"] = quality

    if vcodec:
        paramstore._store["vcodec"] = vcodec

    if noaudio:
        paramstore._store["noaudio"] = True

    if start_time:
        paramstore._store["start_time"] = start_time

    if end_time:
        paramstore._store["end_time"] = end_time

    if get_v_list:
        paramstore._store["get_v_list"] = True

    if retitle:
        paramstore._store["retitle"] = retitle

    if cdm:
        paramstore._store["cdm"] = cdm

    if cache_key:
        paramstore._store["cache_key"] = True

    if no_cache_key:
        paramstore._store["no_cache_key"] = True

    if artisid:
        paramstore._store["artisid"] = artisid
    else:
        paramstore._store["artisid"] = [""]

    paramstore._store["mediaonly"] = mediaonly
    paramstore._store["liveonly"] = liveonly
    paramstore._store["photoonly"] = photoonly
    paramstore._store["noticeonly"] = noticeonly
    paramstore._store["board"] = board
    paramstore._store["cmtonly"] = cmtonly

    if signup:
        paramstore._store["signup"] = True
        
    if change_password:
        paramstore._store["change_password"] = True

    if join_community:
        paramstore._store["join_cm"] = True

    if leave_community:
        paramstore._store["leave_cm"] = True

    if savedir:
        paramstore._store["savedir"] = savedir
        
    if subs_only:
        paramstore._store["subs_only"] = True
        
    if subs_only and no_subs:
        logger.error("Cannot use --subs-only and --no-subs together.")
        raise ValueError("Invalid args error exit")
        
    if no_subs:
        paramstore._store["no_subs"] = True


def had_key() -> bool:
    """是否顯示金鑰並跳過下載"""
    return _get_arg("has_key", False)


def had_nocookie() -> bool:
    """是否禁用 Cookie"""
    return _get_arg("had_nocookie", False)


def clean_dl() -> bool:
    """是否在完成後刪除檔案（預設 True）"""
    value = _get_arg("clean_dl")
    return True if value is None else value


def skip_merge() -> bool:
    """是否跳過合併"""
    return _get_arg("skip_merge", False)


def skip_mux() -> bool:
    """是否跳過封裝"""
    return _get_arg("skip_mux", False)


def fanclub() -> bool:
    """是否僅顯示粉絲俱樂部內容"""
    return _get_arg("fanclub", False)


def nofanclub() -> bool:
    """是否僅顯示非粉絲俱樂部內容"""
    return _get_arg("nofanclub", False)


def community() -> bool:
    """是否顯示社群內容"""
    return _get_arg("community", False)


def change_password() -> bool:
    """是否變更密碼"""
    return _get_arg("change_password", False)


def group() -> str:
    """取得群組名稱（預設 'ive'）"""
    return _get_arg("group", "default_group")


def board() -> bool:
    """是否選擇看板"""
    return _get_arg("board", False)


def cmtonly() -> bool:
    """是否選擇看板"""
    return _get_arg("cmtonly", False)


def join_community() -> str:
    """取得要加入的社群名稱"""
    return _get_arg("join_community", "")


def leave_community() -> str:
    """取得要離開的社群名稱"""
    return _get_arg("leave_community", "")


def time_date1() -> str | None:
    """取得日期範圍 兩個日期"""
    return _get_arg("time_date1", "")


def time_date2() -> str | None:
    """取得日期範圍 兩個日期"""
    return _get_arg("time_date2", "")


def quality() -> str | int | None:
    """Video quality"""
    return _get_arg("quality", "")


def vcodec() -> str | int | None:
    """Video codec"""
    return _get_arg("vcodec", "")


def start_time() -> str | None:
    return _get_arg("start_time", "")


def end_time() -> str | None:
    return _get_arg("end_time", "")


def retitle() -> str | None:
    return _get_arg("retitle", None)


def show_help() -> bool:
    """是否顯示幫助"""
    return _get_arg("show_help", False)


def mediaonly() -> bool:
    """是否僅顯示媒體內容"""
    return _get_arg("mediaonly", False)


def liveonly() -> bool:
    """是否僅顯示直播內容"""
    return _get_arg("liveonly", False)


def photoonly() -> bool:
    """是否僅顯示照片內容"""
    return _get_arg("photoonly", False)


def noticeonly() -> bool:
    """是否僅顯示公告內容"""
    return _get_arg("noticeonly", False)


def signup() -> bool:
    """是否註冊"""
    return _get_arg("signup", False)


def nodl() -> bool:
    """是否跳過下載"""
    return _get_arg("nodl", False)


def nojson() -> bool:
    """是否跳過下載JSON"""
    return _get_arg("nojson", False)


def nothumbnails() -> bool:
    """是否跳過下載封面縮圖"""
    return _get_arg("nothumbnails", False)


def notplaylist() -> bool:
    """是否跳過下載播放清單"""
    return _get_arg("notplaylist", False)


def nohtml() -> bool:
    """是否跳過保存成HTML"""
    return _get_arg("nohtml", False)


def nosubfolder() -> bool:
    """是否不需要子資料夾"""
    return _get_arg("nosubfolder", False)


def noimages() -> bool:
    """是否不需要相片"""
    return _get_arg("noimages", False)


def novideo() -> bool:
    """是否不需要影片"""
    return _get_arg("novideo", False)


def noaudio() -> bool:
    return _get_arg("noaudio", False)


def get_v_list() -> bool:
    return _get_arg("get_v_list", False)


def cdm() -> str:
    return _get_arg("cdm", "")


def cache_key() -> bool:
    return _get_arg("cache_key", False)


def no_cache_key() -> bool:
    return _get_arg("no_cache_key", False)


def artisid() -> str:
    return _get_arg("artisid", "")


def version() -> bool:
    return _get_arg("version", False)


def savedir() -> str|None:
    return _get_arg("savedir", None)


def no_subs() -> bool|None:
    return _get_arg("no_subs", False)


def subs_only() -> bool|None:
    return _get_arg("subs_only", None)


if __name__ == "__main__":
    try:
        main(standalone_mode=False)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        logger.info(f"Program interrupted: {Color.fg('light_gray')}User canceled{Color.reset()}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
else:
    # 模組導入時自動解析（保持兼容性）
    try:
        main(standalone_mode=False)
    except (click.ClickException, SystemExit, RuntimeError):
        pass
    except ValueError as e:
        logger.error(e)
        sys.exit(0)
