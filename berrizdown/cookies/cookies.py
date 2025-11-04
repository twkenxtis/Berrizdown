import asyncio
import base64
import os
import time
from functools import cached_property
from typing import Any, Optional

import jwt

from berrizdown.cookies.loadcookie import LoadCookie
from berrizdown.cookies.pcidgen import PCID
from berrizdown.cookies.Refresh_JWT import Refresh_JWT
from berrizdown.lib.path import Path
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.static.route import Route
from berrizdown.unit.handle.handle_log import setup_logging

route = Route()
DEFAULT_COOKIE: Path = route.default_cookie
file_lock: asyncio.Lock = asyncio.Lock()


logger = setup_logging("cookies", "firebrick")


class Berriz_cookie:
    _instance: Optional["Berriz_cookie"] = None
    show_no_cookie_log: bool = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_cookies"):
            self._cookies: dict[str, Any] = {}
        self.Refresh_JWT: Refresh_JWT = Refresh_JWT()
        self.cookie_bz_r: str = self.loadCookie.cookie_bz_r
        self.cookie_bz_a: str = self.loadCookie.cookie_bz_a
        
    @cached_property
    def loadCookie(self) -> LoadCookie:
        return LoadCookie()

    async def load_cookies(self) -> None:
        """Load cookies from disk."""
        self._cookies = {}
        self._cookies = {"pcid": PCID}
        self._cookies["bz_a"] = self.loadCookie.cookie_bz_a.value
        self._cookies["bz_r"] = self.loadCookie.cookie_bz_r.value
        await self.get_cookies()
        logger.info(f"{Color.fg('chartreuse')}Cookies loaded: {Color.fg('dark_gray')}{list(self._cookies.values())}{Color.reset()}")
        print_jwt_json(self._cookies["bz_a"])

    # 進入點
    async def get_cookies(self) -> dict[str, Any]:
        if paramstore.get("no_cookie") is not True:
            if not os.path.exists(DEFAULT_COOKIE):
                logger.info(f"{Color.fg('orange')}Cant find default.txt, trying to login to create default.txt{Color.reset()}")
                # No cookie using loging to create default.txt
                await self.Refresh_JWT.fsau4021()
            else:
                c: dict[str, Any] = await self.get_valid_cookie()
                return c
        else:
            # no cookie
            return {}
        return {}

    async def get_valid_cookie(self) -> dict[str, Any]:
        cookie: dict[str, Any] = await self.check_hasattr()
        if cookie not in (None, {}):
            return cookie
        raise RuntimeError("Fail to get cookie")

    async def jwt_error_handle(self) -> None:
        await self.Refresh_JWT.refresh_token()
        await self.get_cookies()

    def b64url_decode(self, data: str) -> bytes:
        padding: str = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    async def check_hasattr(self) -> dict[str, Any]:
        if not hasattr(self, "_cookies") or not self._cookies:
            await self.load_cookies()
        return self._cookies


def print_jwt_json(token: str) -> None:
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        header = {"error": f"header parse failed: {e}"}

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        payload = {"error": f"payload parse failed: {e}"}

    data = {"": header, "*": payload}

    def fmt(k, v):
        key = k.lstrip("H*")
        if key in {"iat", "exp", "nbf"} and isinstance(v, (int, float)):
            try:
                v = time.strftime("%H:%M:%S", time.localtime(v))
            except Exception:
                pass
        return f"{k}: {v}"

    logger.info(" ".join(map(lambda kv: fmt(kv[0], kv[1]), [(f"{part}{k}", v) for part, section in data.items() for k, v in section.items()])))
