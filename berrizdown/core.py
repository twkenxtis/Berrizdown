import sys
import requests

from berrizdown.lib.click_types import *
from berrizdown.static.help import print_help
from berrizdown.static.version import __version__

if show_help():
    print_help()
    sys.exit(0)

if version():
    print(f"{Color.fg('yellow')}/" * 26)
    print(f"{Color.fg('aquamarine')}Berrizdown version: {Color.fg('gold')}{__version__}{Color.reset()}")
    print(f"{Color.fg('yellow')}\\" * 26)
    print(Color.reset())
    sys.exit(0)

import rich.traceback
from berrizdown.lib.account.berriz_create_community import BerrizCreateCommunity
from berrizdown.static.color import Color
from berrizdown.unit.community.community import custom_dict, init_cm_for_main
from berrizdown.unit.handle.handle_log import setup_logging

rich.traceback.install()

logger = setup_logging("core", "orange")
from berrizdown.static.parameter import paramstore

# set account to empty string for login.py
paramstore._store["current_account_mail"] = 0
from berrizdown.lib.account.change_pawword import Change_Password
from berrizdown.lib.account.signup import run_signup
from berrizdown.lib.path import Path
from berrizdown.lib.interface.interface import Community_Uniqueness, StartProcess, URL_Parser
from berrizdown.lib.load_yaml_config import CFG
from berrizdown.mystate.parse_my import request_my
from berrizdown.unit.community.community import get_community_print
from berrizdown.unit.date.date import process_time_inputs
from berrizdown.unit.handle.handle_choice import Handle_Choice
from berrizdown.unit.http.request_berriz_api import BerrizAPIClient, GetRequest, WEBView
BAPIClient: BerrizAPIClient = BerrizAPIClient()

time1, time2 = time_date1(), time_date2()
if time_date1() or time_date2():
    time_a, time_b = process_time_inputs(time1, time2)
else:
    time_a, time_b = None, None

async def init():
    await cm_join_leave_main()
    await password_change_main()
    await sign_up_main()

async def click_urls() -> None:
    urls = paramstore.get("click_urls")
    if urls:
        if paramstore.get("no_cookie") is not True:
            await request_my()
        logger.info(f"{Color.bold()}{Color.bg('aluminum')}(URI Mode){Color.reset()}")
        await URL_Parser(urls).parser()
        results_selected_media: list[dict[tuple, str | list[str]]] = await Community_Uniqueness.group_by_community()
        await StartProcess(results_selected_media).process()
        await BAPIClient.close_session()
        sys.exit(0)

async def start():
    bool_version, version_str = version_check()
    if bool_version:
        logger.info(
            f"{Color.bold()}{Color.fg('gold')}[Berrizdown had new version unvailable]{Color.reset()} "
            f"{Color.fg('blue')}{__version__}{Color.reset()}{Color.bold()} → {Color.fg('green')}{version_str}"
            f"{Color.reset()}"
        )
    if paramstore.get("no_cookie") is not True:
        await WEBView().allow_host()
    await init()
    await click_urls()
    GGP = group()
    if Path(cookies_userinput()).exists() is False:
        logger.error(f"{Color.fg('dark_blue')}--cookies {Color.fg('black')}must be a correct path to cookies file{Color.reset()}")
        await BAPIClient.close_session()
        sys.exit(0)
    if start_time() is not None and end_time() is not None and len(str(start_time())) == 0 or len(str(end_time())) == 0:
        await BAPIClient.close_session()
        logger.error(f"{Color.fg('black')}argument got unknown value{Color.reset()}")
        sys.exit(0)
    if not community():
        if GGP == "default_group":
            logger.warning(
                f"Auto choese {Color.fg('spring_green')}group: {Color.fg('red')}Default setting {Color.reset()}"
                f"{Color.bg('gold')}{Color.fg('black')} Use --group (name/id){Color.reset()} "
                f"{Color.fg('aquamarine')}to change group{Color.reset()} "
            )
            GGP = "ive"
        community_id, communityname = await BerrizCreateCommunity(await init_cm_for_main(GGP), GGP).community_id_name()
        custom_name: str | None = await custom_dict(communityname)
        logger.info(
            f"{Color.fg('spring_green')}Current choese community:{Color.reset()} < {Color.fg('turquoise')}{custom_name}{Color.reset()} > ｜{Color.reset()} ( {Color.fg('light_green')}{community_id}{Color.reset()} )"
        )
        logger.info(f"{Color.bold()}{Color.bg('aluminum')}(User Choice Mode){Color.reset()}")
        await Handle_Choice(community_id, communityname, custom_name, time_a, time_b).handle_choice()
    else:
        await get_community_print()
        await BAPIClient.close_session()

async def cm_join_leave_main():
    JM: str = join_community()
    LM: str = leave_community()
    if paramstore.get("join_cm") is True and paramstore.get("no_cookie") is not True:
        await BerrizCreateCommunity(await init_cm_for_main(JM), JM).community_join()
        await BAPIClient.close_session()
    elif paramstore.get("join_cm") is True and paramstore.get("no_cookie") is True:
        logger.warning(f"Cancel join community, {Color.fg('lavender')}Not login{Color.reset()}")
        await BAPIClient.close_session()
        sys.exit(0)
    if paramstore.get("leave_cm") is True and paramstore.get("no_cookie") is not True:
        await BerrizCreateCommunity(await init_cm_for_main(LM), LM).leave_community_main()
        await BAPIClient.close_session()
    elif paramstore.get("leave_cm") is True and paramstore.get("no_cookie") is True:
        logger.warning(f"Cancel leave community, {Color.fg('lavender')}Not login{Color.reset()}")
        await BAPIClient.close_session()
        sys.exit(0)

async def password_change_main():
    if paramstore.get("change_password") is True and paramstore.get("no_cookie") is not True:
        if await Change_Password().change_password() is True:
            logger.info(f"{Color.fg('spring_green')}Password changed!{Color.reset()}")
            await BAPIClient.close_session()
            sys.exit(0)
        else:
            logger.info(f"{Color.fg('dark_green')}Password had not change{Color.reset()}")
            await BAPIClient.close_session()
    elif paramstore.get("change_password") is True and paramstore.get("no_cookie") is True:
        logger.warning(f"Cancel change password, {Color.fg('lavender')}Not login{Color.reset()}")
        await BAPIClient.close_session()
        sys.exit(0)

async def sign_up_main():
    if paramstore.get("signup") is True and paramstore.get("no_cookie") is not True:
        await run_signup()
        await BAPIClient.close_session()
        sys.exit(0)
    elif paramstore.get("signup") is True and paramstore.get("no_cookie") is True:
        logger.warning(f"Cancel signup, {Color.fg('lavender')}Not login{Color.reset()}")
        await BAPIClient.close_session()
        sys.exit(0)

def version_check() -> bool:
    url = 'https://raw.githubusercontent.com/twkenxtis/Berrizdown/refs/heads/main/berrizdown/static/version.py'
    
    try:
        v = requests.get(url).text
    except requests.exceptions.RequestException:
        return False, ""
    
    for line in v.splitlines():
        if line.strip().startswith("__version__"):
            _, rhs = line.split("=", 1)
            version: str = rhs.strip().strip('\'"')
            version: str = version.strip()
            if version != __version__:
                return True, version
            return False, ""
    return False, ""