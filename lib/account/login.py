import re
import sys
from typing import Any
from urllib.parse import ParseResult, parse_qs, urlparse

import httpx
from cookies.loadcookie import LoadCookie
from lib.account.authgen import get_auth_request
from lib.account.unban_account import unban_main
from lib.load_yaml_config import CFG
from lib.path import Path
from static.api_error_handle import api_error_handle
from static.color import Color
from static.parameter import paramstore
from static.route import Route
from unit.handle.handle_log import setup_logging
from unit.http.httpx_login_unban import Request

logger = setup_logging("login", "flamingo_pink")


YAML_PATH: Path = Route().YAML_path
DEFAULT_COOKIE: Path = Route().default_cookie

R: Request = Request()


async def vaild_email(ENMAIL: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "email": ENMAIL,
    }
    url: str = "https://account.berriz.in/member/v1/members:email-exists"
    response: httpx.Response = await R.get(url, params)
    return response.json()


async def authorizeKey(challenge: str, state: str, CLIENTID: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "clientId": CLIENTID,
        "codeChallenge": challenge,
        "challengeMethod": "S256",
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": "/",
        "state": state,
        "languageCode": "en",
    }
    url: str = "https://account.berriz.in/auth/v1/authorize:init"
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(url, params=params)
        try:
            return response.json()
        except AttributeError:
            return {"Internet response error"}


async def get_code(CLIENTID: str, challenge: str, state_csrf: str, authenticatekey: str) -> str | None:
    params: dict[str, Any] = {
        "clientId": CLIENTID,
        "codeChallenge": challenge,
        "challengeMethod": "S256",
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": "/",
        "state": state_csrf,
        "authenticateKey": authenticatekey,
    }
    url: str = "https://account.berriz.in/auth/v1/authorize"
    response: httpx.Response = await R.get(url, params)
    location_header: str | None = response.headers.get("location")
    return location_header


async def authenticateKey(
    authorizeKey: str,
    challenge: str,
    state_csrf: str,
    ENMAIL: str,
    PASSWORD: str,
    CLIENTID: str,
) -> dict[str, Any]:
    json_data: dict[str, Any] = {
        "password": PASSWORD,
        "clientId": CLIENTID,
        "authorizeKey": authorizeKey,
        "challengeMethod": "S256",
        "codeChallenge": challenge,
        "state": state_csrf,
        "email": ENMAIL,
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": "/",
    }
    url: str = "https://account.berriz.in/auth/v1/authenticate"
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.post(url, json=json_data)
        return response.json()


async def token_issue(CLIENTID: str, code_value: str, code_verifier: str) -> dict[str, Any]:
    json_data: dict[str, Any] = {
        "code": code_value,
        "clientId": CLIENTID,
        "codeVerifier": code_verifier,
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": "/",
    }
    url: str = "https://account.berriz.in/auth/v1/token:issue"
    response: httpx.Response = await R.post(url, json_data)
    return response.json()


def extract_url_params(url_string: str) -> tuple[str | None, str | None]:
    """
    從網址字串中解析並提取 'code' 和 'postRedirectUri' 參數
    """
    parsed_url: ParseResult = urlparse(url_string)
    query_params: dict[str, list[str]] = parse_qs(parsed_url.query)
    code: str | None = query_params.get("code", [None])[0]
    postRedirectUri: str | None = query_params.get("postRedirectUri", [None])[0]
    return code, postRedirectUri


class LoginManager:
    EMAIL_REGEX: "re.Pattern[str]" = re.compile(r".+@.+\..+")
    CLIENTID: str = "e8faf56c-575a-42d2-933d-7b2e279ad827"

    def __init__(self):
        self.LC: LoadCookie = LoadCookie()
        self.account: str | None = None
        self.password: str | None = None
        self.bz_a: str | None = None
        self.bz_r: str | None = None

    def no_vaild_account_password(self) -> None:
        logger.info("No valid account/password found in YAML!")
        current: Path = Path.cwd()
        yamlpath: Path = current.joinpath(YAML_PATH)
        invaild_cookies = self.LC.find_all_cookiejars()
        if invaild_cookies == [] or DEFAULT_COOKIE.exists():
            logger.info(f"{Color.fg('orange')}Follow the steps below to login {Color.fg('tan')}[default.txt|account:password]: {Color.reset()}")
            logger.info(
                f"Try setting {Color.fg('orange')}{yamlpath} {Color.reset()}{Color.fg('light_gray')}"
                f"at {Color.fg('green')}berriz.account{Color.fg('light_gray')} in YAML {Color.fg('tan')}['email':'password']{Color.reset()}"
            )
            logger.info(
                f"Try {Color.fg('orange')}put Netscape cookie {Color.reset()}{Color.fg('light_gray')}"
                f"at {Color.fg('green')}berriz\\cookies\\Berriz{Color.fg('light_gray')} in Folder {Color.fg('tan')}Make sure cookie name is default.txt{Color.reset()}"
            )
            for ck in invaild_cookies:
                logger.info(f"{Color.fg('light_gray')}Try rename it to default.txt and check cookie is in Berriz folder{Color.reset()}{Color.fg('light_green')} {ck}{Color.reset()}")
        raise ValueError("No valid account/password in YAML")

    async def load_info(self) -> bool:
        cfg_account_info: dict[list[str, str]] = CFG["berriz"]["account"]
        if not isinstance(cfg_account_info, list):
            raise TypeError("Yaml account must be a List")
        current_account: int = paramstore.get("current_account_mail")
        n = len(cfg_account_info) - 1
        if current_account < len(cfg_account_info):
            n = current_account
        try:
            email = cfg_account_info[n]["email"]
            password = cfg_account_info[n]["password"]
            if LoginManager.EMAIL_REGEX.match(email) and len(password) > 7:
                self.account = email
                self.password = password
                sucess_bool: bool = await self.run_login()
                if sucess_bool:
                    current_account += 1
                    paramstore._store["current_account_mail"] = current_account
                    return True
            self.no_vaild_account_password()
        except ValueError as e:
            logger.error(f"{e} - Fail to use account password re-login in")

    async def run_login(self, email: str = None, password: str = None) -> bool:
        # 校驗郵箱
        ok: bool = await self.check_mail()
        if not ok:
            return False
        # PKCE 請求
        challenge, state, verifier = get_auth_request()
        if not all(
            (
                self.check_challenge(challenge),
                self.check_state(state),
                self.check_code_verifier(verifier),
            )
        ):
            return False
        # authorizeKey
        authkey_data: dict[str, Any] = await authorizeKey(challenge, state, self.CLIENTID)
        authkey: str = await self.check_authkey(authkey_data)
        # authenticateKey
        ak_data: dict[str, Any] = await authenticateKey(
            authkey,
            challenge,
            state,
            email or self.account,
            password or self.password,
            self.CLIENTID,
        )
        authk: str = await self.check_authenticatekey(ak_data)
        # 拿到重定向 URL 回應header裡面有資料
        location: str | None = await get_code(self.CLIENTID, challenge, state, authk)
        if not self.check_location_url(location or ""):
            return False

        # 提取 code from 回應header的資料
        code, _ = extract_url_params(location or "")
        if not self.check_code_value(code or ""):
            return False

        # PKCE 發起請求 set-cookie 取得
        tokens: dict[str, Any] = await token_issue(self.CLIENTID, code or "", verifier)
        if not self.check_bz_a_bz_r(tokens):
            return False

        # 確認 bz_a bz_r 返回 True 到 cookie.py 完成 Login
        pair: tuple[str, str] | None = self.sort_bz_a_bz_r(tokens)
        if not pair:
            return False

        self.bz_a, self.bz_r = pair
        return True

    async def check_mail(self) -> bool:
        info: dict[str, Any] = await vaild_email(self.account or "")
        if info["code"] == "0000":
            if not info["data"]["exists"]:
                raise ValueError(f"Account does not exist: {self.account}")
            return True
        if info["code"] in ("FS_ME2120", "FS_AU4020", "FS_AU4021"):
            return False
        raise Exception("Unknown error at check_mail")

    async def check_authkey(self, data: dict[str, Any]) -> str:
        try:
            if data["code"] != "0000":
                raise ValueError(f"Auth key error: {data}")
        except (KeyError, TypeError):
            raise ValueError(f"Auth key error: {data}")
        key: str = data["data"]["authorizeKey"]
        if not key or len(key) != 30:
            raise ValueError(f"Bad authorizeKey: {key}")
        return key

    async def check_authenticatekey(self, data: dict[str, Any]) -> str:
        code: str = data["code"]
        if code != "0000":
            if code == "FS_AU4030":
                logger.error(f"{api_error_handle(code)}")
                """{'code': 'FS_AU4030', 'message': 'Unfortunately, 
                your account has been suspended. Additional authentication is required to re-enable.'}"""
                if await unban_main(self.account) is True:
                    logger.info(f"{Color.fg('light_green')}Account unlocked ! Please login again.{Color.reset()}")
                    print(f"{Color.fg('yellow')}Program exit now, Please manuel restart or put new default.txt{Color.reset()}")
                    sys.exit(0)
            else:
                raise ValueError(f"Authenticate key error: {data}")
        key: str = data.get("data", {}).get("authenticateKey", "")
        if not key or len(key) != 30:
            raise ValueError(f"Bad authenticateKey: {key}")
        else:
            return key

    def check_challenge(self, ch: str) -> bool:
        return len(ch) == 64

    def check_state(self, st: str) -> bool:
        return len(st) == 21

    def check_code_verifier(self, cv: str) -> bool:
        return len(cv) == 21

    def check_location_url(self, url: str) -> bool:
        return url.startswith("https://berriz.in/auth/token?code=") and len(url) >= 110

    def check_code_value(self, code: str) -> bool:
        return code is not None and len(code) == 30

    def check_bz_a_bz_r(self, data: dict[str, Any]) -> bool:
        return data.get("code") == "0000" and isinstance(data.get("data"), dict)

    def sort_bz_a_bz_r(self, data: dict[str, Any]) -> tuple[str, str] | None:
        d: dict[str, Any] = data["data"]
        a: Any = d.get("accessToken")
        r: Any = d.get("refreshToken")
        if isinstance(a, str) and isinstance(r, str) and len(a) == 598 and len(r) > 79:
            return a.strip(), r.strip()
        return None

    async def new_refresh_cookie(self) -> tuple[str | None, str | None]:
        return self.bz_a, self.bz_r
