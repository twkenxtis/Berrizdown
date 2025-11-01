import re
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from lib.account.authgen import AuthManager, create_auth_request
from static.api_error_handle import api_error_handle
from static.color import Color
from unit.handle.handle_log import setup_logging
from unit.http.httpx_login_unban import Request
from unit.http.request_berriz_api import BerrizAPIClient

logger = setup_logging("signup", "periwinkle")


# 密碼強度正則表達式檢查
_pw_re: re.Pattern[str] = re.compile(
    r"^"  # Start of string
    r"(?=.*[A-Za-z])"  # 至少一個字母
    r"(?=.*\d)"  # 至少一個數字
    r'(?=.*[!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])'  # 至少一個特殊字符
    r"[\x20-\x7E]{8,32}"  # 可列印 ASCII 字符, 長度 8-32
    r"$"  # End of string
)

CLIENTID: str = "e8faf56c-575a-42d2-933d-7b2e279ad827"


R = Request()


async def valid_email(email: str) -> bool | None:
    """
    檢查電子郵件是否存在（已註冊）
    """
    params: dict[str, str] = {
        "email": email,
        "languageCode": "en",
    }
    url: str = "https://account.berriz.in/member/v1/members:signup-email-exists"
    response: httpx.Response = await R.get(url, params)
    response_json: dict[str, Any] = response.json()
    code: str = response_json.get("code")
    if code == "0000":
        # 預期是 False E-mail不存在Berriz資料庫紀錄
        return response_json.get("data", {}).get("exists")
    elif code != "0000":
        logger.warning(f"{api_error_handle(code)} → {email}")
        return None
    else:
        logger.error(response_json)
        raise Exception(response_json)


async def step2(email: str) -> bool:
    """
    請求發送驗證碼到電子郵件
    """
    json_data: dict[str, str] = {
        "sendTo": email,
    }
    url: str = "https://account.berriz.in/member/v1/verification-emails:send/SIGN_UP"
    response: httpx.Response = await R.post(url, json_data)
    response_json: dict[str, Any] = response.json()

    if response_json.get("code") == "0000":
        return True
    else:
        logger.error(response_json)
        return False


async def post_verification_key(email: str, otpInt: str) -> str | None:
    """
    提交 OTP 碼並獲取 verifiedKey
    """
    json_data: dict[str, str] = {
        "email": email,
        "otpCode": otpInt,
    }
    url: str = "https://account.berriz.in/member/v1/verification-emails:verify/SIGN_UP"
    response: httpx.Response = await R.post(url, json_data)
    response_json: dict[str, Any] = response.json()
    code: str = response_json.get("code")
    if code == "0000" and response_json.get("message") == "OK":
        verifiedKey: str | None = response_json.get("data", {}).get("verifiedKey")
        if verifiedKey and len(verifiedKey) == 36:
            return verifiedKey
        else:
            logger.error("verifiedKey not valid uuid")
            raise ValueError("Check verifiedKey is uuid or not.")
    elif code == "FS_ME2050":
        logger.error(f"{response_json.get('message')}{Color.reset()} {Color.fg('magenta_pink')}Please re-enter {email} and password to continue")
        await SignupManager(email, "").sign_up()
        return None
    else:
        logger.error(response_json)
        return None


async def terms(email: str, password: str, verifiedKey: str) -> bool:
    """
    提交會員註冊資訊，包含服務條款接受
    """
    json_data: dict[str, Any] = {
        "email": email,
        "password": password,
        "verifiedKey": verifiedKey,
        "acceptTermSet": [
            {
                "termKey": "0193608e-f5bb-6c0b-6996-ba7a603abe02",
                "isAccepted": True,
            },
            {
                "termKey": "0193608f-cd05-65e9-b56d-e74dead216b9",
                "isAccepted": True,
            },
        ],
        "hasAgreedToAgeLimit": True,
    }
    url: str = "https://account.berriz.in/member/v1/members:sign-up"
    response: httpx.Response = await R.post(url, json_data)
    response_json: dict[str, Any] = response.json()
    code: str = response_json.get("code")
    if code == "0000" and response_json.get("message") == "OK":
        return True
    elif code != "0000":
        logger.error(f"{api_error_handle(code)}")
        return False
    else:
        logger.error(response_json)
        raise Exception(response_json)


async def authorizeKey(codeChallenge: str, state: str, clientId: str) -> str | None:
    """
    獲取授權金鑰 (authorizeKey)
    """
    params: dict[str, str] = {
        "clientId": clientId,
        "codeChallenge": codeChallenge,
        "challengeMethod": "S256",
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": "/",
        "state": state,
        "languageCode": "en",
    }
    url: str = "https://account.berriz.in/auth/v1/authorize:init"
    response: httpx.Response = await R.get(url, params)
    response_json: dict[str, Any] = response.json()

    if response_json.get("code") == "0000" and response_json.get("message") == "OK":
        return response_json.get("data", {}).get("authorizeKey")
    else:
        logger.error(response_json)
        raise Exception(response_json)


async def authenticateKey(
    authorizeKey: str,
    challenge: str,
    state_csrf: str,
    ENMAIL: str,
    PASSWORD: str,
    CLIENTID: str,
) -> str:
    """
    提交憑證並獲取認證金鑰 (authenticateKey)
    """
    json_data: dict[str, str] = {
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
    response: httpx.Response = await R.post(url, json_data)
    response_json: dict[str, Any] = response.json()
    code: str = response_json.get("code")
    if code == "0000":
        key: str | None = response_json.get("data", {}).get("authenticateKey")
        if not key or len(key) != 30:
            raise ValueError(f"Bad authenticateKey: {key}")
        return key
    elif code == "FS_AU4002":
        logger.error(response_json.get("message"))
        raise ValueError("DATA_INVALID")
    else:
        logger.error(response_json)
        raise Exception(response_json)


async def get_code(CLIENTID: str, challenge: str, state_csrf: str, authenticatekey: str) -> str | None:
    """
    使用 authenticateKey 換取授權碼 (code)，返回包含 code 的 location header URL
    """
    params: dict[str, str] = {
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


async def token_issue(CLIENTID: str, code_value: str, code_verifier: str) -> dict[str, Any]:
    """
    使用授權碼 (code) 和 code_verifier 獲取存取令牌 (token)
    """
    json_data: dict[str, str] = {
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
    parsed_url = urlparse(url_string)
    query_params: dict[str, list[str]] = parse_qs(parsed_url.query)
    code: str | None = query_params.get("code", [None])[0]
    postRedirectUri: str | None = query_params.get("postRedirectUri", [None])[0]
    return code, postRedirectUri


class SignupManager:
    """
    處理會員註冊和密碼相關檢查的管理器
    """

    def __init__(self, email: str, password: str) -> None:
        self.account: str = (email or "").strip().lower()
        self.password: str = (password or "").strip()
        self.CLIENTID: str = CLIENTID

    def validate_password_regex(self) -> bool:
        """檢查密碼是否符合強度要求"""
        return bool(_pw_re.match(self.password))

    def check_challenge(self, ch: str) -> bool:
        """檢查 code challenge 長度"""
        return len(ch) == 64

    def check_state(self, st: str) -> bool:
        """檢查 state 長度"""
        return len(st) == 21

    def check_code_verifier(self, cv: str) -> bool:
        """檢查 code verifier 長度"""
        return len(cv) == 21

    def check_location_url(self, url: str) -> bool:
        """檢查 location URL 格式"""
        return url.startswith("https://berriz.in/auth/token?code=") and len(url) > 110

    def check_code_value(self, code: str | None) -> bool:
        """檢查授權碼 (code) 值"""
        return code is not None and len(code) == 30

    def check_bz_a_bz_r(self, data: dict[str, Any]) -> bool:
        """檢查 token 響應是否成功"""
        return data.get("code") == "0000" and isinstance(data.get("data"), dict)

    def sort_bz_a_bz_r(self, data: dict[str, Any]) -> tuple[str, str] | None:
        """提取並驗證 access_token 和 refresh_token"""
        d: dict[str, Any] = data.get("data", {})
        a: Any = d.get("accessToken")
        r: Any = d.get("refreshToken")
        # 這裡假設 access token 長度為 598 是有效的驗證標準 和 refresh token 長度為 80 以上是有效的驗證標準 (bz_r 長度不一定 80是隨機測試的avg)
        if isinstance(a, str) and isinstance(r, str) and len(a) == 598 and len(r) > 79:
            return a.strip(), r.strip()
        return None

    @staticmethod
    def get_auth_request(password: str, clientId: str) -> tuple[str, str, str]:
        """
        生成並返回 PKCE 相關的 challenge, state, verifier
        (新增了 @staticmethod 裝飾器)
        """
        res: dict[str, Any] = create_auth_request(
            password=password,
            authorize_key="",
            email="",
            challenge_method="S256",
            post_redirect_uri="/",
            clientid=clientId,
        )
        m: AuthManager = res["auth_manager"]
        return m.challenge, m.state, m.code_verifier

    async def sign_up(self) -> str | bool:
        """
        執行完整的會員註冊流程
        """
        if not self.validate_password_regex():
            logger.warning("Your password must contain 8 to 32 alphanumeric and special characters")
            return False

        # PKCE 請求
        codeChallenge, state, verifier = SignupManager.get_auth_request(self.password, self.CLIENTID)
        if not all(
            (
                self.check_challenge(codeChallenge),
                self.check_state(state),
                self.check_code_verifier(verifier),
            )
        ):
            return False

        email_exists: bool | None = await valid_email(self.account)
        if email_exists is False:
            if await step2(self.account):
                otpInt: str = self.handle_user_input()
                verifiedKey: str | None = await post_verification_key(self.account, otpInt)

                if verifiedKey:
                    if await terms(self.account, self.password, verifiedKey) is True:
                        authkey: str | None = await authorizeKey(codeChallenge, state, self.CLIENTID)
                        if authkey:
                            ak_data: str = await authenticateKey(
                                authkey,
                                codeChallenge,
                                state,
                                self.account,
                                self.password,
                                self.CLIENTID,
                            )
                            return f"{Color.fg('gray')}One-time auth temp_token: {ak_data}{Color.reset()} Success create account → {Color.fg('gold')}{self.account}"
            return False
        elif email_exists is True:
            logger.info(f"{self.account}: This email address is already registered")
            return False
        else:
            # valid_email 返回 None 或拋出異常的情況
            return False

    def handle_user_input(self) -> str:
        """
        處理 CLI 上的使用者輸入 OTP 碼
        """
        prompt: str = f"{Color.fg('light_gray')}Enter the {Color.fg('violet')}6-digit code {Color.fg('light_gray')}you received via email: {Color.fg('gold')}{self.account} {Color.reset()}"
        while True:
            logger.info(f"{Color.fg('bright_yellow')}{prompt}{Color.reset()}")
            try:
                otp_code: str = input(prompt).strip()
            except EOFError:
                logger.error("Input not available. Cannot prompt for OTP code.")
                raise

            if otp_code.isdigit() and len(otp_code) == 6:
                return otp_code
            logger.warning("Invalid OTP: must be exactly 6 digits")


async def run_signup() -> None:
    EMAIL_REGEX: re.Pattern[str] = re.compile(r".+@.+\..+")
    logger.info(f"{Color.bg('magenta')}{Color.fg('platinum')}Start signup process for Berriz{Color.reset()}")
    try:
        while True:
            email = input(f"{Color.fg('light_gray')}Enter a {Color.fg('teal')}email{Color.reset()}{Color.fg('light_gray')} you want to register be account: {Color.reset()}")
            if EMAIL_REGEX.match(email):
                logger.info("Password is contain 8 to 32 alphanumeric and special characters.")
                password = input(f"{Color.fg('light_gray')}Enter {Color.bg('apple_green')}password{Color.reset()}{Color.fg('light_gray')}: {Color.reset()}")
                resp = await SignupManager(email, password).sign_up()
                if resp is not False:
                    logger.info(f"{resp}{Color.reset()} | {Color.fg('cyan')}{password}{Color.reset()}")
                    break
            else:
                logger.warning("Invalid email format")
        await BerrizAPIClient().close_session()
        sys.exit(0)
    except EOFError:
        pass
