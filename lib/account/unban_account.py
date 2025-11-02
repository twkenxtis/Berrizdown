import sys
from typing import Any

from httpx import Response
from static.api_error_handle import api_error_handle
from static.color import Color
from unit.handle.handle_log import setup_logging
from unit.http.httpx_login_unban import Request

logger = setup_logging("unban_account", "linen")


R = Request()


async def berriz_verification_email_code(email: str) -> bool:
    """
    請求發送解鎖驗證碼到指定郵箱
    不會和資料庫拿帳號 ID 或 OAUTH 驗證，未註冊過也會發送
    """
    json_data: dict[str, str] = {"sendTo": email}
    try:
        response: Response = await R.post(
            "https://account.berriz.in/member/v1/verification-emails:send/UNBLOCK",
            json_data,
        )
    except RuntimeError:
        return False

    response_json: dict[str, Any] = response.json()

    if response.status_code == 201:
        if response_json.get("code") == "0000":
            return True
        elif response_json.get("code") != "0000":
            logger.error(api_error_handle(response_json.get("code")))
            raise RuntimeWarning("Max exceeded e-mail code")
        return False  # 未知錯誤
    else:
        logger.error(f" {response.status_code} 'https://account.berriz.in/member/v1/verification-emails:send/UNBLOCK'")
        return False


async def post_verification_key(email: str, otpInt: str) -> str | None:
    """
    驗證用戶收到的 OTP 碼，並獲取 verifiedKey
    """
    json_data: dict[str, str] = {"email": email, "otpCode": otpInt}
    try:
        response: Response = await R.post(
            "https://account.berriz.in/member/v1/verification-emails:verify/UNBLOCK",
            json_data,
        )
    except RuntimeError:
        return None

    response_json: dict[str, Any] = response.json()
    code: str | None = response_json.get("code")

    if code == "0000":
        return response_json["data"]["verifiedKey"]
    elif code == "FS_ME2050":
        logger.warning(f"{Color.fg('golden')}{response_json.get('message', 'Code expired')} resend a new code for {Color.reset()}{email}")
        await unban_main(email)

    if code not in ("0000", "FS_ME2050"):
        logger.error("Fail to get verifiedKey")
        return None
    return None


async def member_unlock(email: str, verifiedKey: str) -> bool:
    """
    使用 verifiedKey 發起解鎖會員帳號的請求
    """
    json_data: dict[str, str] = {"email": email, "verifiedKey": verifiedKey}

    try:
        response: Response = await R.put(
            "https://account.berriz.in/member/v1/members:unblock",
            json_data,
        )
    except RuntimeError:
        return False

    response_json: dict[str, Any] = response.json()
    code: str | None = response_json.get("code")

    if code == "0000":
        logger.info(f"{Color.fg('green')}{response_json.get('message', 'Account unlocked successfully')}{Color.reset()}")
        return True
    elif code != "0000":
        logger.warning(f"{response_json.get('message', 'Error 5010')} {api_error_handle(code)}")
        return False
    logger.error(f"{Color.fg('golden')}{response_json.get('message', 'Unknown unlock error')}{Color.reset()}")
    return False


def handle_user_input(email: str) -> str:
    """
    處理並驗證用戶輸入的 6 位數 OTP 碼
    """
    while True:
        logger.info(f"{Color.fg('bright_magenta')}Auto start unban account, Please enter the 6-digit code you received via email: {Color.fg('yellow')}{email} {Color.reset()}")
        otpCode: str = input(f"{Color.fg('honeydew')}Enter the 6-digit code you received via email:{Color.reset()} {Color.fg('yellow')}{email} {Color.reset()}").strip()

        if otpCode.isdigit() and len(otpCode) == 6:
            otpInt: str = otpCode.strip()
            return otpInt
        logger.warning("Invalid OTP: must be exactly 6 digits")


async def unban_main(email: str) -> bool:
    """
    主解鎖流程：發送郵箱驗證碼 -> 獲取用戶輸入 -> 獲取 Verified Key -> 解鎖帳號
    """
    email = email.strip().lower()

    try:
        if await berriz_verification_email_code(email):
            otpInt: str = handle_user_input(email)
            verification_key: str | None = await post_verification_key(email, otpInt)

            if verification_key is not None:
                if await member_unlock(email, verification_key):
                    logger.info(f"{Color.fg('light_gray')}Your account {Color.fg('yellow')}{email} {Color.fg('gold')}has been unlocked. {Color.fg('green')}Please login again{Color.reset()}")
                    return True
                else:
                    sys.exit(1)
            else:
                return False  # post_verification_key 返回 None
        else:
            return False  # berriz_verification_email_code 返回 False

    except RuntimeWarning:
        # 處理郵箱發送次數超限
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred in unban_main: {e}", exc_info=True)
        return False
