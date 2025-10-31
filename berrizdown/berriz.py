try:
    import asyncio

    from lib.click_types import *
    from static.help import print_help

    if show_help():
        print_help()
        sys.exit(0)

    if version():
        sys.exit(0)

    import rich.traceback
    from lib.account.berriz_create_community import BerrizCreateCommunity
    from static.color import Color
    from unit.community.community import custom_dict, init_cm_for_main
    from unit.handle.handle_log import setup_logging

    rich.traceback.install()

    logger = setup_logging("berriz", "orange")
    from static.parameter import paramstore

    # set account to empty string for login.py
    paramstore._store["current_account_mail"] = 0
    from lib.account.change_pawword import Change_Password
    from lib.account.signup import run_signup
    from lib.interface.interface import Community_Uniqueness, StartProcess, URL_Parser
    from mystate.parse_my import request_my
    from unit.community.community import get_community_print
    from unit.date.date import process_time_inputs
    from unit.handle.handle_choice import Handle_Choice
    from unit.http.request_berriz_api import BerrizAPIClient, WEBView

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

    async def main():
        if paramstore.get("no_cookie") is not True:
            await WEBView().allow_host()
        await init()
        await click_urls()
        GGP = group()
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

except KeyboardInterrupt as e:
    if str(e) == "":
        logger.info(f"Program interrupted: {Color.fg('light_gray')}User canceled{Color.reset()}")
    else:
        logger.warning(f"Program interrupted: {Color.fg('light_gray')}{e}{Color.reset()}")
except RuntimeError as e:
    if str(e) == "Event loop is closed":
        logger.warning(f"Program interrupted: {Color.fg('light_gray')}Event loop is closed re-run the program.{Color.reset()}")
        asyncio.run(main())
    else:
        raise e
except NameError:
    pass
