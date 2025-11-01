import asyncio
import json
import logging
import random
import re
import sys
import ssl
import time
import uuid
from functools import lru_cache, cached_property
from itertools import repeat
from typing import Any

import aiohttp
from cookies.cookies import Refresh_JWT
from lib.base64 import base64
from lib.load_yaml_config import CFG
from lib.lock_cookie import Lock_Cookie, cookie_session
from lib.Proxy import Proxy
from pydantic import BaseModel, Field, ValidationError
from static.api_error_handle import api_error_handle
from static.color import Color
from static.parameter import paramstore
from unit.__init__ import USERAGENT
from unit.handle.handle_log import setup_logging

logger = setup_logging("request_berriz_api", "aluminum")

_session: aiohttp.ClientSession | None = None


class CreateCommunityModel(BaseModel):
    """Pydantic model for create_community payload"""

    communityId: int
    name: str
    communityTermsIds: list[int] = Field(default_factory=list)


class UpdatePasswordModel(BaseModel):
    """Pydantic model for update_password payload"""

    currentPassword: str
    newPassword: str


class TranslatePostModel(BaseModel):
    """Pydantic model for translate_post payload"""

    postId: str
    translateLanguageCode: str


class TranslateCommentModel(BaseModel):
    """Pydantic model for translate_comment payload"""

    commentId: int
    translateLanguageCode: str


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def handle_response(obj):
    if obj is None:
        raise ValueError("response is None")

    logger.debug(f"Response: {obj}, {type(obj)}")
    raw_response = obj

    # Early returns for primitives
    if isinstance(obj, str):
        return raw_response
    if isinstance(obj, (bytes, aiohttp.ClientResponse)):
        return raw_response

    # Unpack if needed
    if isinstance(obj, list):
        if not obj:
            return raw_response
        obj = obj[0]

    if not isinstance(obj, dict):
        raise TypeError(f"Cannot process response: {obj!r}")

    if obj.get("code") != "0000":
        try:
            error_msg = api_error_handle(obj["code"])
            logger.warning(f"{error_msg} | {Color.fg('mint')}{raw_response}{Color.reset()}")
        except KeyError:
            if any(keyword in obj.get("message", "").lower() for keyword in ("success", "ok")):
                return obj
            else:
                logger.error(f"Unknown error: {raw_response}")
    return raw_response


class BerrizAPIClient:
    show_proxy_log: bool = True
    base_sleep: float = CFG["BerrizAPIClient"]["base_sleep"]
    max_sleep: float = CFG["BerrizAPIClient"]["max_sleep"]
    max_retries: int = CFG["BerrizAPIClient"]["max_retries"]
    retry_http_status: frozenset[int] = frozenset({400, 401, 403, 502, 503, 504})
    _re_request_cookie: bool = True

    def __init__(self) -> None:
        self.headers: dict[str, str] = self._build_headers()
        self._ssl_context: ssl.SSLContext | None = None

    def _create_optimized_ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ctx.set_ciphers("ECDHE+AESGCM")
        ctx.options |= ssl.OP_NO_COMPRESSION
        ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        ctx.load_default_certs()
        ctx.session_stats()
        return ctx

    def get_session(self) -> aiohttp.ClientSession:
        global _session
        if _session is None:
            ssl_ctx = self._create_optimized_ssl_context()
            connector = aiohttp.TCPConnector(
                ssl=ssl_ctx,
                limit=CFG["BerrizAPIClient"]["connector_limit"],
                limit_per_host=CFG["BerrizAPIClient"]["connector_limit_per_host"],
                keepalive_timeout=CFG["BerrizAPIClient"]["keepalive_timeout"],
                enable_cleanup_closed=CFG["BerrizAPIClient"]["enable_cleanup_closed"],
                force_close=CFG["BerrizAPIClient"]["force_close"],
                use_dns_cache=CFG["BerrizAPIClient"]["use_dns_cache"],
                ttl_dns_cache=CFG["BerrizAPIClient"]["ttl_dns_cache"],
                resolver=aiohttp.AsyncResolver(),
            )

            timeout = aiohttp.ClientTimeout(
                total=CFG["BerrizAPIClient"]["timeouttotal"],
                connect=CFG["BerrizAPIClient"]["timeeoutconnect"],
                sock_connect=CFG["BerrizAPIClient"]["timeoutsock_connect"],
                sock_read=CFG["BerrizAPIClient"]["timeeoutsock_read"],
            )

            _session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True,
            )

            logger.info(f"{Color.fg('sage')}[Generate new session] {Color.fg('fog')}Timeout: {_session.timeout}-Each connect: {connector.limit_per_host} MAX connect: {connector.limit}{Color.reset()}")
        return _session

    async def close_session(self):
        global _session
        if _session is not None:
            await _session.close()
            _session = None

    @lru_cache(maxsize=1)
    def _build_headers(self) -> dict[str, str]:
        return {
            "host": "svc-api.berriz.in",
            "referer": "https://berriz.in/",
            "origin": "https://berriz.in",
            "accept": "application/json",
            "pragma": "no-cache",
            "user-agent": f"{USERAGENT}",
        }

    async def ensure_cookie(self) -> dict[str, str]:
        for _ in repeat(None, 3):
            cookie: dict[str, str] | None = await Lock_Cookie.cookie_session()
            if cookie and isinstance(cookie, dict):
                return cookie
        raise RuntimeError("Fail to get cookie")

    def is_jwt_expiring_soon(self, gwt: str | None) -> bool:
        if gwt is None:
            return False
        if gwt == {}:
            return False
        try:
            if len(gwt) == 0:
                return False
            p = gwt.split(".")[1]
            p += "=" * (-len(p) % 4)
            return int(json.loads(base64.urlsafe_b64decode(p))["exp"]) - time.time() < 150
        except Exception as e:
            logger.error(f"{e}")
            return False

    async def cookie(self, re_request_cookie: bool = False) -> dict[str, str] | None:
        if paramstore.get("no_cookie") is not True:
            if re_request_cookie is True:
                bz_a: str | None = await Refresh_JWT().refresh_token()
                if bz_a is not None:
                    cookie: dict[str, str] = await self.ensure_cookie()
                    cookie["bz_a"] = bz_a
                    return cookie
                else:
                    #TODO: input for catch user cooke?
                    logger.error("Cookie is none.")
                    await self.close_session()
                    sys.exit(0)

            if cookie_session in (None, {}):
                BerrizAPIClient._re_request_cookie = False
                cookie: dict[str, str] = await self.ensure_cookie()
                return cookie
            else:
                return cookie_session
        elif paramstore.get("no_cookie") is True:
            return {}

    async def _get_random_proxy(self) -> str:
        """Select a random proxy from the proxy list, throttled to one call per second."""
        raw: str = random.choice(Proxy._load_proxies())
        raw = raw.strip().rstrip(",")
        try:
            host, port, user, password = raw.split(":", maxsplit=3)
            proxy_url: str = f"http://{user}:{password}@{host}:{port}"
        except ValueError:
            proxy_url: str = raw
        return proxy_url

    async def _send_request(
        self,
        method: str,  # "get", "post", "patch", "options"
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        use_proxy: bool = False,
        usecookie: bool = True,
        response_object: bool = False,
        json_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | str | bytes | dict[str, Any] | aiohttp.ClientResponse | None:
        max_retries: int = self.max_retries
        attempt: int = 0
        while attempt < max_retries:
            session: aiohttp.ClientSession = self.get_session()
            cookies, proxy = await self._prepare_session(use_proxy, usecookie)
            if not cookies and usecookie and paramstore.get("no_cookie") != True:
                raise RuntimeError("Cookie is empty! cancel request")

            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    cookies=cookies,
                    headers=headers or self.headers,
                    json=json_data,
                    proxy=proxy,
                    ssl=True,
                ) as response:
                    await self._log_response(response, method, url, params)

                    if response.status in self.retry_http_status:
                        message: str = await response.text()
                        await self._handle_retry_errors(response, message)

                    if response.status == 403 and ("policy/webview-host/allows" in url or "service/v1/my/geo-location" in url):
                        """most like proxy got CloudFront block"""
                        logger.error(f"{response.status} {url} {response.status} {response.reason} {response.headers}")
                        raise KeyboardInterrupt("Not allowed, exit.")

                    if response_object:
                        return response

                    return await self._process_response_content(response)

            except aiohttp.ClientResponseError as e:
                result = await self._handle_client_error(e, url)
                if result is not None:
                    return result
                attempt += 1

            except (TimeoutError, aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, aiohttp.ClientOSError, aiohttp.ClientPayloadError) as e:
                await self._handle_connection_error(e, attempt, max_retries)
                attempt += 1

        logger.error(f"Retry exceeded for {url}")
        return None

    async def _prepare_session(self, use_proxy: bool, usecookie: bool) -> tuple[dict[str, str], str | None]:
        ck: dict[str, str] | None = await self.cookie()

        if self.is_jwt_expiring_soon(ck.get("bz_a") if ck else None):
            await self.cookie(True)
            ck: dict[str, str] | None = await self.cookie()
        # TODO: current only http/https and no VPN support.
        proxy: str | None = await self._get_random_proxy()
        proxy = proxy if use_proxy else None

        cookies: dict[str, str] = ck if usecookie and ck else {}
        return cookies, proxy

    async def _log_response(self, response: aiohttp.ClientResponse, method: str, url: str, params: dict) -> None:
        if CFG["BerrizAPIClient"]["show_log"] is True:
            logger.info(f"{Color.fg('gray')}{response.status} {method.upper()} {response.real_url}{Color.reset()}")
        logger.debug(response.request_info)
        logger.debug(f"Cookies: {response.cookies}")

    async def _handle_retry_errors(self, response: aiohttp.ClientResponse, message: str) -> None:
        if any(code in message for code in ("FS_ER5030", "FS_AU1023")):
            # return the JSON error
            return await response.json()

        if message in ("FS_ER4020", "FS_AU4020", "FS_AU4021", "Jwt is expired", "Jwt is not in the form of Header.Payload.Signature with two dots and 3 sections"):
            # force refresh cookie
            await self.cookie(True)

        raise aiohttp.ClientResponseError(
            request_info=response.request_info,
            history=response.history,
            status=response.status,
            message=message,
            headers=response.headers,
        )

    async def _process_response_content(self, response: aiohttp.ClientResponse) -> str | bytes | dict[str, Any]:
        try:
            return await response.json()
        except aiohttp.ContentTypeError:
            try:
                return await response.text()
            except UnicodeDecodeError:
                return await response.read()

    async def _handle_client_error(
        self,
        e: aiohttp.ClientResponseError,
        url: str,
    ) -> dict[str, Any] | None:
        if e.status in (401, 403):
            if e.status == 403 and "svc-api.berriz.in/service/v1/translate/" in url:
                logger.info(
                    f"Translate API is often got speed limit error "
                    f"{Color.bg('tan')}{Color.fg('ruby')}403{Color.bg('tan')} on {Color.reset()}"
                    f"{Color.fg('orange')} translate endpoint, {Color.reset()}"
                    f"{Color.fg('khaki')}abandoning request: {Color.reset()}"
                    f"{Color.fg('bright_gray')} {url}{Color.reset()}"
                )
                return {}

            else:
                logger.error(f"HTTP error for {url}: {e} {Color.bg('gold')}status={e.status}{Color.reset()}")
                return None

        logger.error(f"Unhandled ClientResponseError: {e}")
        return None

    async def _handle_connection_error(self, e: Exception, attempt: int, max_retries: int) -> None:
        logger.warning(f"{Color.fg('yellow')}Connection error ({type(e).__name__}){Color.reset()}, {Color.fg('light_slate_gray')}retry {attempt + 1}/{max_retries}: {e}{Color.reset()}")
        sleep: float = min(self.max_sleep, self.base_sleep * (2**attempt))
        sleep *= 0.7310585786300049 + random.random()
        logger.info(f"Sleeping for {sleep:.2f} seconds")
        await asyncio.sleep(sleep)


class Playback_info(BerrizAPIClient):
    async def get_playback_context(self, media_ids: str | list[str], use_proxy: bool) -> list[dict[str, Any]]:
        media_ids = [media_ids] if isinstance(media_ids, str) else media_ids
        results: list[dict[str, Any]] = []

        for media_id in media_ids:
            if isinstance(media_id, str) and is_valid_uuid(media_id):
                params: dict[str, str] = {"languageCode": "en"}
                url: str = f"https://svc-api.berriz.in/service/v1/medias/{media_id}/playback_info"
                if data := await self._send_request("get", url, params, self.headers, use_proxy):
                    results.append(data)
            else:
                logger.warning(f"Invalid media ID format: {media_id}")

        return await handle_response(results)

    async def get_live_playback_info(self, media_ids: str | list[str], use_proxy: bool) -> list[dict[str, Any]]:
        """Fetch playback information for given media IDs."""
        media_ids = [media_ids] if isinstance(media_ids, str) else media_ids
        results: list[dict[str, Any]] = []

        for media_id in media_ids:
            if isinstance(media_id, str) and is_valid_uuid(media_id):
                params: dict[str, str] = {"languageCode": "en"}
                url: str = f"https://svc-api.berriz.in/service/v1/medias/live/replay/{media_id}/playback_area_context"
                if data := await self._send_request("get", url, params, self.headers, use_proxy):
                    results.append(data)
            else:
                logger.warning(f"Invalid media ID format: {media_id}")

        return await handle_response(results)


class Public_context(BerrizAPIClient):
    async def get_public_context(self, media_ids: str | list[str], use_proxy: bool) -> list[dict[str, Any]]:
        media_ids = [media_ids] if isinstance(media_ids, str) else media_ids
        results: list[dict[str, Any]] = []

        for media_id in media_ids:
            if isinstance(media_id, str) and is_valid_uuid(media_id):
                params: dict[str, str] = {"languageCode": "en"}
                url: str = f"https://svc-api.berriz.in/service/v1/medias/{media_id}/public_context"
                if data := await self._send_request("get", url, params, self.headers, use_proxy, False):
                    results.append(data)
            else:
                logger.warning(f"Invalid media ID format: {media_id}")

        return await handle_response(results)


class Live(BerrizAPIClient):
    async def request_live_playlist(self, playback_url: str, media_id: str, use_proxy: bool) -> str | None:
        """Request m3u8 playlist."""
        if not playback_url:
            logger.error(f"{Color.fg('light_gray')}No playback URL provided for media_id{Color.reset()}: {Color.fg('turquoise')}{media_id}{Color.reset()}")
            return None

        params: dict[str, str] = {"": ""}
        headers: dict[str, str] = {
            "user-Agent": f"{USERAGENT}",
            "accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
            "referer": "Berriz/20250704.1139 CFNetwork/1498.700.2 Darwin/23.6.0",
        }

        try:
            if response := await self._send_request("get", playback_url, params, headers, use_proxy, False):
                return await handle_response(response, use_proxy)
        except aiohttp.ClientError as e:
            logger.error(f"{Color.fg('plum')}Failed to get m3u8 list for media_id{Color.reset()} {Color.fg('turquoise')}{media_id}{Color.reset()}{Color.fg('plum')}: {e}{Color.reset()}")
            return None

    async def fetch_mpd(self, url: str, use_proxy: bool) -> str | None:
        usecookie = False
        params = {}
        headers = {
            "user-agent": f"{USERAGENT}",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "connection": "close",
            "pragma": "no-cache",
            "cache-control": "no-cache",
        }

        d = await self._send_request("get", url, params, headers, use_proxy, usecookie, response_object=False)
        if d is not None:
            return await handle_response(d)

    async def fetch_statics(self, media_seq: int, use_proxy: bool) -> dict[str, Any] | None:
        """Fetch static media information for the given media sequence."""
        try:
            if int(media_seq) is None:
                logger.error("Cannot fetch statics: media_seq is not provided.")
        except AttributeError:
            logger.error("Cannot fetch statics: media_seq is not provided.")
            raise ValueError("media_seq is None.")

        params: dict[str, str] = {
            "languageCode": "en",
            "mediaSeq": f"{int(media_seq)}",
            "t": "1",
        }

        url: str = "https://svc-api.berriz.in/service/v1/media/statics"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def fetch_chat(self, current_second: int, media_seq: int, use_proxy: bool) -> dict[str, Any] | None:
        """Fetch chat data for the given media sequence and time."""
        if int(media_seq) is None:
            logger.error("Cannot fetch chat: media_seq is not provided.")
            return None

        params: dict[str, str] = {
            "languageCode": "en",
            "translateLanguageCode": "en",
            "mediaSeq": f"{int(media_seq)}",
            "t": f"{current_second}",
        }

        url: str = "https://chat-api.berriz.in/chat/v1/sync"
        headers: dict[str, str] = {
            **self.headers,
            "host": "chat-api.berriz.in",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        d = await self._send_request("get", url, params, headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def fetch_live_replay(self, community_id: str | int, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        Community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/medias/live/end"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)


class Notify(BerrizAPIClient):
    async def fetch_notify(self, community_id: str, param: dict[str, Any], use_proxy: bool) -> dict | None:
        language_code = param.get("languageCode", "en")
        page_size = param.get("pageSize", 100)
        next = param.get("next", "")

        if community_id == "":
            params: dict[str, str] = {
                "languageCode": language_code,
                "pageSize": page_size,
                "next": next,
            }
        else:
            params: dict[str, str] = {
                "languageCode": language_code,
                "communityId": community_id,
                "pageSize": page_size,
                "next": next,
            }

        url: str = "https://svc-api.berriz.in/service/v1/notifications"
        headers: dict[str, str] = {
            "user-Agent": f"{USERAGENT}",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "alt-Used": "svc-api.berriz.in",
        }

        if response := await self._send_request("get", url, params, headers, use_proxy):
            return await handle_response(response)

        logger.warning(f"{Color.fg('bright_red')}Failed to obtain notification information{Color.reset()}")
        return None


class My(BerrizAPIClient):
    
    params: dict[str, str] = {"languageCode": "en"}
    
    async def fetch_location(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/my/geo-location"
        d = await self._send_request("get", url, My.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def fetch_home(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/home"
        d = await self._send_request("get", url, My.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def fetch_my(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/my"
        d = await self._send_request("get", url, My.params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def notifications(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/notifications:new"
        d = await self._send_request("get", url, My.params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def fetch_me(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://account.berriz.in/auth/v1/accounts"
        headers: dict[str, str] = {
            "User-Agent": f"{USERAGENT}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Alt-Used": "account.berriz.in",
        }
        d = await self._send_request("get", url, My.params, headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def fetch_fanclub(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/fanclub/products/subscription"
        d = await self._send_request("get", url, My.params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def get_me_info(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://account.berriz.in/member/v1/members/me"
        headers: dict[str, str] = {
            "user-Agent": f"{USERAGENT}",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "alt-Used": "account.berriz.in",
        }
        d = await self._send_request("get", url, My.params, headers, use_proxy)
        if d is not None:
            return await handle_response(d)


class Community(BerrizAPIClient):
    
    params: dict[str, str] = {"languageCode": "ko"}
    
    async def community_keys(self, use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/community/keys"
        d = await self._send_request("get", url, Community.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def community_menus(self, communityId: int, use_proxy: bool) -> dict[str, Any] | None:
        Community_id_checker(communityId)
        url: str = f"https://svc-api.berriz.in/service/v1/community/info/{communityId}/menus"
        d = await self._send_request("get", url, Community.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def community_name(self, use_proxy: bool) -> dict[str, Any] | None:
        url = "https://svc-api.berriz.in/service/v1/my/state"
        d = await self._send_request("get", url, Community.params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def community_id(self, communityname: str, use_proxy: bool) -> dict[str, Any] | None:
        url = f"https://svc-api.berriz.in/service/v1/community/id/{communityname}"
        d = await self._send_request("get", url, Community.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def create_community(self, communityId: int, name: str, use_proxy: bool) -> dict[str, Any] | None:
        usecookie: bool = True
        response_object: bool = False
        Community_id_checker(communityId)

        # Use Pydantic for validation
        try:
            payload = CreateCommunityModel(communityId=communityId, name=name, communityTermsIds=[])
            json_data = payload.model_dump()
        except ValidationError as e:
            logger.error(f"Validation error in create_community: {e}")
            return None

        url: str = "https://svc-api.berriz.in/service/v1/community/user/create"
        d = await self._send_request(
            "post",
            url,
            Community.params,
            self.headers,
            use_proxy,
            usecookie,
            response_object,
            json_data,
        )

        if d is not None:
            return await handle_response(d)

    async def leave_community(self, communityId: int, use_proxy: bool) -> dict[str, Any] | None:
        usecookie: bool = True
        response_object: bool = False
        params: dict[str, int | str] = {
            "communityId": communityId,
            "languageCode": "en",
        }

        Community_id_checker(communityId)
        url: str = "https://svc-api.berriz.in/service/v1/community/user/withdraw"
        json_data = {}

        d = await self._send_request(
            "post",
            url,
            params,
            self.headers,
            use_proxy,
            usecookie,
            response_object,
            json_data,
        )

        if d is not None:
            return await handle_response(d)


class MediaList(BerrizAPIClient):
    async def media_list(self, community_id: int | str, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        Community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/medias/recent"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)


class GetRequest(BerrizAPIClient):
    async def get_request(self, url: str, use_proxy: bool) -> aiohttp.ClientResponse | None:
        usecookie = False
        params = {}

        d = await self._send_request(
            "get",
            url,
            params,
            self.headers,
            use_proxy,
            usecookie,
            response_object=False,
        )

        if d is not None:
            return await handle_response(d)


class GetPost(BerrizAPIClient):
    async def get_post(
        self,
        url: str,
        json_data: dict[str, Any],
        params: dict[str, Any],
        headers: dict[str, str],
        use_proxy: bool,
    ) -> aiohttp.ClientResponse | None:
        usecookie: bool = False
        response_object: bool = False

        d = await self._send_request(
            "post",
            url,
            params,
            headers,
            use_proxy,
            usecookie,
            response_object,
            json_data,
        )

        if d is not None:
            return await handle_response(d)


_pw_re: re.Pattern = re.compile(
    r"^"  # Start of string
    r"(?=.*[A-Za-z])"  # At least one letter
    r"(?=.*\d)"  # At least one digit
    r'(?=.*[!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])'  # At least one special character
    r"[\x20-\x7E]{8,32}"  # Printable ASCII characters, length 8-32
    r"$"  # End of string
)


class Password_Change(BerrizAPIClient):
    def validate_password_regex(self, password: str) -> bool:
        return bool(_pw_re.match(password))

    async def update_password(self, currentPassword: str, newPassword: str, use_proxy: bool) -> dict[str, Any] | None:
        usecookie: bool = True
        response_object: bool = False

        if self.validate_password_regex(newPassword) and self.validate_password_regex(currentPassword) is False:
            logging.warning("Your password must contain 8 to 32 alphanumeric and special characters")
            raise ValueError("Invaild password formact")

        if self.validate_password_regex(newPassword) and self.validate_password_regex(currentPassword) is True:
            params: dict[str, str] = {"languageCode": "en"}

            # Use Pydantic for validation
            try:
                payload = UpdatePasswordModel(currentPassword=currentPassword, newPassword=newPassword)
                json_data = payload.model_dump()
            except ValidationError as e:
                logger.error(f"Validation error in update_password: {e}")
                return None

            headers: dict[str, str] = {
                "user-agent": f"{USERAGENT}",
                "accept": "application/json",
                "referer": "https://berriz.in/",
                "content-Type": "application/json",
                "origin": "https://berriz.in",
                "alt-Used": "account.berriz.in",
            }

            url: str = "https://account.berriz.in/auth/v1/accounts:update-password"
            d = await self._send_request(
                "patch",
                url,
                params,
                headers,
                use_proxy,
                usecookie,
                response_object,
                json_data,
            )

            if d is not None:
                return await handle_response(d)

        return None


class Arits(BerrizAPIClient):
    def __init__(self) -> None:
        self.headers: dict[str, str] = self.header()
        self.params: dict[str, str] = {"languageCode": "en"}
        
    @cached_property
    def community_id_checker(self) -> "Community_id_checker":
        return Community_id_checker

    def header(self) -> dict[str, str]:
        return {
            "user-agent": f"{USERAGENT}",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "alt-Used": "svc-api.berriz.in",
            "accept-encoding": "gzip, deflate",
        }

    async def artis_list(self, community_id: int, use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/artists"
        d = await self._send_request("get", url, self.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def artis_comment(self, community_id: int, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/comment/{community_id}/artists/comments"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def user_comment(self, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        url: str = "https://svc-api.berriz.in/service/v1/comment/comments"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def comment(self, comment_id: int, use_proxy: bool) -> dict[str, Any] | None:
        url: str = f"https://svc-api.berriz.in/service/v1/comment/comments/{comment_id}"
        d = await self._send_request("get", url, self.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def comment_replies(
        self,
        community_id: int,
        contentTypeCode: str | int,
        contentId: str | int,
        parent_seq: str | int,
        use_proxy: bool,
    ) -> dict[str, Any] | None:
        params: dict[str | int, str | int] = {
            "contentTypeCode": contentTypeCode,
            "contentId": contentId,
            "pageSize": "999999999",
            "languageCode": "en",
        }
        url: str = f"https://svc-api.berriz.in/service/v1/comment/{community_id}/artists/{parent_seq}/replies"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def _board_list(self, board_id: str, community_id: str, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/boards/{board_id}/feed"
        d = await self._send_request("get", url, params, self.headers, use_proxy, True)
        if d is not None:
            return await handle_response(d)

    async def arits_archive(self, community_id: int, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v2/community/{community_id}/artist/archive"
        d = await self._send_request("get", url, params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def arits_archive_v1(self, community_id: int, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/artist/archive"
        d = await self._send_request("get", url, params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def arits_archive_with_cmartisId(
        self,
        community_id: int,
        cmartis_id: str,
        params: dict[str, Any],
        use_proxy: bool,
    ) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v2/community/{community_id}/artist/{cmartis_id}/archive"
        d = await self._send_request("get", url, params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)

    async def post_detil(self, community_id: int, post_uuid: str, use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/post/{post_uuid}"
        d = await self._send_request("get", url, self.params, self.headers, use_proxy, True)
        if d is not None:
            return await handle_response(d)

    async def request_notice(self, community_id: int, params: dict[str, Any], use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/notices"
        d = await self._send_request("get", url, params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)

    async def request_notice_page(self, community_id: int, communityNoticeId: int, use_proxy: bool) -> dict[str, Any] | None:
        self.community_id_checker(community_id)
        url: str = f"https://svc-api.berriz.in/service/v1/community/{community_id}/notices/{communityNoticeId}"
        d = await self._send_request("get", url, self.params, self.headers, use_proxy, False)
        if d is not None:
            return await handle_response(d)


class Translate(BerrizAPIClient):
    async def translate_post(self, post_id: int, target_lang: str, use_proxy: bool) -> str | None:
        usecookie: bool = False
        response_object: bool = False

        if not post_id:
            logger.error("Text to translate cannot be empty.")
            return None

        params: dict[str, str] = {"languageCode": "en"}
        url: str = "https://svc-api.berriz.in/service/v1/translate/post"

        # Use Pydantic for validation
        try:
            payload = TranslatePostModel(postId=str(post_id), translateLanguageCode=target_lang)
            json_data = payload.model_dump()
        except ValidationError as e:
            logger.error(f"Validation error in translate_post: {e}")
            return None

        data: dict[str, Any] | None = await self._send_request(
            "post",
            url,
            params,
            self.headers,
            use_proxy,
            usecookie,
            response_object,
            json_data,
        )

        if data is None:
            return ""

        result: str | None = data.get("data", {}).get("result")
        return await handle_response(result) if result else None

    async def translate_comment(self, contentTypeCode: int, target_lang: str, use_proxy: bool) -> str | None:
        usecookie: bool = False
        response_object: bool = False

        if not contentTypeCode:
            logger.error("Text to translate cannot be empty.")
            return None

        params: dict[str, str] = {"languageCode": "en"}
        url: str = "https://svc-api.berriz.in/service/v1/translate/comment"

        # Use Pydantic for validation
        try:
            payload = TranslateCommentModel(commentId=contentTypeCode, translateLanguageCode=target_lang)
            json_data = payload.model_dump()
        except ValidationError as e:
            logger.error(f"Validation error in translate_comment: {e}")
            return None

        data: dict[str, Any] | None = await self._send_request(
            "post",
            url,
            params,
            self.headers,
            use_proxy,
            usecookie,
            response_object,
            json_data,
        )

        if data is None:
            return ""

        result: str | None = data.get("data", {}).get("result")
        return await handle_response(result) if result else None


class WEBView(BerrizAPIClient):
    async def allow_host(self) -> dict[str, Any] | None:
        use_proxy: bool = False
        params: dict[str, str] = {"languageCode": "en"}
        url: str = "https://svc-api.berriz.in/service/v1/app/policy/webview-host/allows"
        d = await self._send_request("get", url, params, self.headers, use_proxy)
        if d is not None:
            return await handle_response(d)


class TPD_RemoteCDM_Request(BerrizAPIClient):
    def __init__(self, secret: str) -> None:
        self.usecookie: bool = False
        self.response_object: bool = False
        self.headers: dict[str, str] = {
            "user-agent": "Berriz/20250912.1136 CFNetwork/1498.700.2 Darwin/23.6.0",
            "accept-encoding": "gzip, deflate",
            "accept": "*/*",
            "x-secret-key": secret,
        }
        
    async def get(self, url: str, use_proxy: bool)-> dict[str, Any] | None:
        d = await self._send_request(
            "get",
            url,
            {},
            self.headers,
            use_proxy,
            self.usecookie,
            self.response_object,
        )
        if d is not None:
            return await handle_response(d)

    async def post(self, url: str, json_data: dict[str, Any], use_proxy: bool)-> dict[str, Any] | None:
        d = await self._send_request(
            "post",
            url,
            {},
            self.headers,
            use_proxy,
            self.usecookie,
            self.response_object,
            json_data,
        )
        if d is not None:
            return await handle_response(d)
        
        
class Community_id_checker:
    def __init__(self, community_id: int | str) -> None:
        self.input = community_id
        self.check_community_id()

    def check_community_id(self) -> None:
        try:
            communityId = int(self.input)
            if not isinstance(communityId, int):
                raise ValueError
        except ValueError:
            logger.error(f"{Color.fg('red')}communityId should be int {Color.reset()} Current is ⭢ {Color.bg('ruby')}{self.input}")
            raise ValueError(f"Value {Color.bg('ruby')}{self.input}{Color.reset()} should be int")
