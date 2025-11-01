import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx


class AuthManager:
    # 單例管理：確保全局只有一個 AuthManager 實例
    _instance: Optional["AuthManager"] = None

    # 動態建立屬性於 create()/from_dict() 中
    code_verifier: str
    challenge: str
    state: str
    created_at: datetime
    expires_at: datetime

    @classmethod
    def create(cls, challenge_method: str = "S256") -> "AuthManager":
        """
        - 生成 code_verifier code_challenge state
        - 設定實例的有效期限 7 分鐘
        """
        instance: AuthManager = cls()
        # 生成 21 字符 code_verifier
        instance.code_verifier = cls._generate_code_verifier()
        # 根據 code_verifier 生成相同格式的 code_challenge
        instance.challenge = cls._generate_challenge(instance.code_verifier, challenge_method)
        # 生成防 CSRF 的 state - 21 字符
        instance.state = cls._generate_state()
        # 實例時間標記與過期時間
        instance.created_at = datetime.now()
        instance.expires_at = instance.created_at + timedelta(minutes=7)
        return instance

    @classmethod
    def get(cls) -> Optional["AuthManager"]:
        """
        獲取現有的認證管理器實例，對應 JS 端 a.R.get() 的行為
        只有在實例存在且未過期時才返回，否則返回 None
        """
        inst: AuthManager | None = cls._instance
        if inst and inst._is_valid():
            return inst
        return None

    @classmethod
    def _generate_code_verifier(cls) -> str:
        """
        1. 16 字節隨機數據
        2. Base64-URL 編碼
        3. 移除 '=' 填充
        4. 截斷至 21 字符
        """
        random_bytes: bytes = secrets.token_bytes(16)
        verifier: str = base64.urlsafe_b64encode(random_bytes).decode()
        verifier = verifier.replace("=", "")  # 去掉填充符
        return verifier[:21]  # 確保長度

    @classmethod
    def _generate_challenge(cls, code_verifier: str, method: str = "S256") -> str:
        """
        - S256: 對 code_verifier 做 SHA256，輸出HEX字串 = 64 字符
        - plain: 直接返回 code_verifier
        """
        if method == "S256":
            digest: bytes = hashlib.sha256(code_verifier.encode()).digest()
            # JS 端使用十六進製輸出，而非 Base64
            challenge: str = digest.hex()
            return challenge
        elif method == "plain":
            return code_verifier
        else:
            raise ValueError(f"Unsupported challenge method: {method}")

    @classmethod
    def _generate_state(cls) -> str:
        """
        - 16 字節隨機數據
        - Base64-URL 編碼
        - 去除 '=' 填充
        - 截斷至 21 字符
        """
        random_bytes: bytes = secrets.token_bytes(16)
        state: str = base64.urlsafe_b64encode(random_bytes).decode().replace("=", "")
        return state[:21]

    def _is_valid(self) -> bool:
        """檢查單例實例是否在有效期限內"""
        return datetime.now() < self.expires_at

    def to_dict(self) -> dict[str, str]:
        """
        轉換實例為字典 用於持久化存儲
        包含 code_verifier / challenge / state / 7MIN
        """
        return {
            "code_verifier": self.code_verifier,
            "challenge": self.challenge,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "AuthManager":
        """
        從字典恢復AuthManager實例
        """
        instance: AuthManager = cls()
        instance.code_verifier = data["code_verifier"]
        instance.challenge = data["challenge"]
        instance.state = data["state"]
        instance.created_at = datetime.fromisoformat(data["created_at"])
        instance.expires_at = datetime.fromisoformat(data["expires_at"])
        cls._instance = instance
        return instance

    def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        post_redirect_uri: str = "/",
        language_code: str = "en",
    ) -> str:
        """
        生成 OAuth 授權請求的 URL
        """
        base_url: str = "https://account.berriz.in/auth/v1/authorize:init"
        params: dict[str, str] = {
            "clientId": client_id,
            "codeChallenge": self.challenge,
            "challengeMethod": "S256",
            "redirectUri": redirect_uri,
            "postRedirectUri": post_redirect_uri,
            "state": self.state,
            "languageCode": language_code,
        }
        # httpx.QueryParams 自動處理 URL 編碼
        return f"{base_url}?{httpx.QueryParams(params)}"


def create_auth_request(
    password: str,
    authorize_key: str,
    email: str,
    clientid: str,
    challenge_method: str = "S256",
    post_redirect_uri: str | None = None,
) -> dict[str, Any]:
    auth_manager: AuthManager = AuthManager.get() or AuthManager.create(challenge_method)

    request_data: dict[str, Any] = {
        "password": password,
        "clientId": clientid,
        "authorizeKey": authorize_key,
        "challengeMethod": challenge_method,
        "codeChallenge": auth_manager.challenge,
        "state": auth_manager.state,
        "email": email,
        "redirectUri": "https://berriz.in/auth/token",
        "postRedirectUri": post_redirect_uri,
    }
    # 移除 None 項，保持請求參數乾淨
    request_data = {k: v for k, v in request_data.items() if v is not None}
    return {
        "auth_manager": auth_manager,  # 保存實例用於後續 token 發行
        "request_data": request_data,
        "request_config": {
            "url": "https://account.berriz.in/auth/v1/authenticate",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": request_data,
        },
    }


def get_auth_request():
    res: dict[str, Any] = create_auth_request(
        password="",
        authorize_key="",
        email="",
        challenge_method="S256",
        post_redirect_uri="/",
        clientid="e8faf56c-575a-42d2-933d-7b2e279ad827",
    )
    m: AuthManager = res["auth_manager"]
    return m.challenge, m.state, m.code_verifier
