import asyncio
from datetime import datetime
from typing import Any
from functools import cached_property


import aiohttp
import jwt
from cookies.loadcookie import LoadCookie
from lib.account.login import LoginManager
from lib.path import Path
from static.color import Color
from static.parameter import paramstore
from static.route import Route
from unit.handle.handle_log import setup_logging

route = Route()
DEFAULT_COOKIE: Path = route.default_cookie
file_lock: asyncio.Lock = asyncio.Lock()

logger = setup_logging("Refresh_JWT", "khaki")


class Refresh_JWT:
    no_expires_log: bool = False
    show_no_passwd_log: bool = True
    fsau4021_log: bool = True
    no_LOGIN_log: bool = True

    def __init__(self):
        self.cookie_bz_r: str = self.loadCookie.cookie_bz_r
        self.cookie_bz_a: str = self.loadCookie.cookie_bz_a

    @cached_property
    def LM(self) -> LoginManager:
        return LoginManager()

    @cached_property
    def loadCookie(self) -> LoadCookie:
        return LoadCookie()

    async def refresh_token(self) -> str | None:
        """Refresh the JWT token and save it to bz_a"""
        try:
            data: dict[str, Any] = await _send_post_http(self.cookie_bz_r.value)
        except AttributeError:
            return ""
        if data.get("code", "") == "FS_AU4021":
            if Refresh_JWT.fsau4021_log is True:
                Refresh_JWT.fsau4021_log = False
                logger.warning(f"{data['code']} - {data['message']}")
                bz_a, bz_r = await self.fsau4021()
                return bz_a
        else:
            access_token: str = data.get("data", {}).get("accessToken", "")
            try:
                decoded: dict[str, Any] = jwt.decode(access_token, options={"verify_signature": False})
                exp_time: str = datetime.fromtimestamp(decoded["exp"]).strftime("%Y-%m-%d %H:%M:%S")
                if Refresh_JWT.no_expires_log is False:
                    logger.info(f"{Color.fg('beige')}Token expires at {exp_time}{Color.reset()}")
                    Refresh_JWT.no_expires_log = True
            except Exception as e:
                logger.warning(f"Failed to decode token: {e}")
            self.loadCookie.update_cookie("bz_a", access_token)
            self.loadCookie.save()
        return access_token

    async def fsau4021(self) -> tuple[str | None, str | None]:
        if paramstore.get("no_cookie") is not True:
            if await self.LM.load_info() is True:
                bz_a, bz_r = await self.LM.new_refresh_cookie()
                if bz_a and bz_r:
                    if await self.update_cookie_file(bz_a, bz_r) is True:
                        return bz_a, bz_r
                    else:
                        logger.warning(f"Response: {bz_a} | {bz_r}, Check default.txt why cant write value into file.")
                        raise OSError("Failed to update cookie file")
                else:
                    return None, None
            else:
                logger.info(f"{Color.fg('light_gray')}Token refresh failed, {Color.fg('light_red')}try auto re-login stil {Color.fg('gold')}Fail{Color.reset()}")
                logger.warning(f"{Color.fg('light_gray')}If dont cookie pls use command {Color.reset()}{Color.bg('cyan')}-nc{Color.reset()}{Color.fg('pink')} to continue ...{Color.reset()}")
                return None, None
        else:
            return None, None

    async def update_cookie_file(self, bz_a_new: str | None, bz_r_new: str | None) -> bool:
        if bz_a_new is None or bz_r_new is None:
            return False
        try:
            self.loadCookie.update_cookie("bz_a", bz_a_new)
            self.loadCookie.update_cookie("bz_r", bz_r_new)
            self.loadCookie.save()
            return True
        except Exception as e:
            logger.error(f"Failed to update cookie file: {e}")
            return False

    async def refresh(self) -> str | None:
        """Refresh token"""
        access_token: str | None = await self.refresh_token()
        if access_token:
            return access_token
        else:
            logger.error("Initial token refresh failed")
            return "null"

    async def main(self) -> bool | None:
        """Main method to handle token refresh if needed."""
        bz_a_new: str | None = await self.refresh()
        if bz_a_new is None:
            return False
        if bz_a_new == "null":
            return False
        self.loadCookie.update_cookie("bz_a", bz_a_new)
        self.loadCookie.save()
        return True


async def _send_post_http(bz_r: str) -> dict | None:
    url = "https://account.berriz.in/auth/v1/token:refresh"
    timeout = aiohttp.ClientTimeout(total=7)
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "bz_r": bz_r,
    }
    try:
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.post(
                url,
                headers=headers,
                json={"clientId": "e8faf56c-575a-42d2-933d-7b2e279ad827"},
                ssl=True,
            ) as response:
                logger.info(f"{response.status} {url} {response.reason}")
                if response is not None:
                    return await response.json()
                else:
                    raise aiohttp.ClientError("No response")
    except aiohttp.ClientConnectorError as e:
        logger.warning(f"{Color.fg('light_gray')}Request connection error:{Color.reset()} {Color.fg('periwinkle')}{url}{Color.reset()} - {e}")
    except asyncio.CancelledError:
        logger.warning(f"{Color.fg('light_gray')}Request cancelled{Color.reset()}")
        return
    return None
