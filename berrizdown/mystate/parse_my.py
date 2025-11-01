import asyncio
from typing import Any

from lib.__init__ import use_proxy
from lib.lock_cookie import Lock_Cookie, cookie_session
from rich import box
from rich.console import Console
from rich.table import Table
from static.color import Color
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import My

logger = setup_logging("parse_my", "sunrise")
MY: My = My()


async def request_my() -> None:
    """
    異步請求多個使用者相關的 API 端點，處理 Cookie，並記錄解析後的個人資訊
    """
    if not cookie_session:
        await Lock_Cookie.cookie_session()

    results = await asyncio.gather(
        MY.fetch_my(use_proxy),
        MY.fetch_location(use_proxy),
        MY.notifications(use_proxy),
        MY.fetch_me(use_proxy),
        MY.get_me_info(use_proxy),
        return_exceptions=True,
    )
    exceptions = [r for r in results if isinstance(r, Exception)]
    if exceptions:
        logger.error(f"Exceptions occurred: {exceptions}")
        return
    data, locat, notif, my_data, me = results
    if None in (data, locat, notif, my_data, me):
        logger.warning("One or more API calls returned None")
        return

    my_id: str | None = data.get("data", {}).get("memberInfo", {}).get("memberKey")
    my_email: str | None = data.get("data", {}).get("memberInfo", {}).get("memberEmail")
    location: str | None = locat.get("data", {}).get("countryCode")

    me_info_1: dict[str, Any] = my_data.get("data", {})
    memberKey: str | None = me_info_1.get("memberKey")
    email: str | None = me_info_1.get("email")
    passwordRegistered: bool | None = me_info_1.get("passwordRegistered")
    passwordMismatchCount: int | None = me_info_1.get("passwordMismatchCount")
    status: str | None = me_info_1.get("status")
    createdAt: str | None = me_info_1.get("createdAt")
    updatedAt: str | None = me_info_1.get("updatedAt")

    me_info_2: dict[str, Any] = me.get("data", {})
    email2: str | None = me_info_2.get("email")
    contactEmail: str | None = me_info_2.get("contactEmail")
    country: str | None = me_info_2.get("country")
    phoneNumber: str | None = me_info_2.get("phoneNumber")

    join_community: list[dict[str, Any]] = notif.get("data", {}).get("contents", [])
    keys: list[str] = [key for item in join_community if (key := item.get("communityKey")) is not None]
    console = Console()

    table = Table(title="", show_header=False, box=box.ROUNDED, border_style="bright_blue")

    table.add_row("[bright_white]Login to[/]", f"[red]{my_id}[/]")
    table.add_row("[sky_blue1]Mail[/]", f"[light_sky_blue1]{my_email}[/]")
    table.add_row("[bright_magenta]Location[/]", f"[yellow]{location}[/]")

    table.add_row("[orange1]memberKey[/]", f"[navajo_white1]{memberKey}[/]")
    table.add_row("[medium_purple1]email[/]", f"[plum1]{email}[/]")
    table.add_row("[gold3]passwordRegistered[/]", f"[light_yellow]{passwordRegistered}[/]")
    table.add_row(
        "[light_salmon1]passwordMismatchCount[/]",
        f"[orange3]{passwordMismatchCount}[/]",
    )
    table.add_row("[light_steel_blue]status[/]", f"[light_goldenrod1]{status}[/]")
    table.add_row("[medium_spring_green]createdAt[/]", f"[light_sky_blue1]{createdAt}[/]")
    table.add_row("[deep_pink3]updatedAt[/]", f"[medium_purple]{updatedAt}[/]")

    table.add_row("[light_sea_green]email (me_info_2)[/]", f"[red3]{email2}[/]")
    table.add_row("[dark_orange3]contactEmail[/]", f"[light_cyan]{contactEmail}[/]")
    table.add_row("[light_sky_blue3]country[/]", f"[gold1]{country}[/]")
    table.add_row("[medium_orchid]phoneNumber[/]", f"[light_goldenrod2]{phoneNumber}[/]")

    console.print(table)

    if keys:
        logger.info(f"{Color.fg('gray')}My joined community: {Color.fg('pink')}{' | '.join(keys)}")
