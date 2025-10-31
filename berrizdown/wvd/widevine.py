import httpx
from lib.load_yaml_config import CFG
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
from unit.handle.handle_log import setup_logging

logger = setup_logging("widevine", "navy")


class WidevineDRM:
    # 類別屬性型別註釋
    device: Device
    cdm: Cdm
    session_id: bytes  # 根據 pywidevine 文件，session_id 是一個 bytes 類型

    def __init__(self, device_path: str) -> None:
        # device 和 cdm 假設為 pywidevine 庫中定義的型別
        self.device: Device = Device.load(device_path)
        self.cdm: Cdm = Cdm.from_device(self.device)
        self.session_id: bytes = self.cdm.open()

    # get_license_key 是一個非同步方法，接受 str 參數，回傳 List[str] 或 None
    async def get_license_key(self, pssh: str, acquirelicenseassertion: str) -> list[str] | None:
        req_pssh: PSSH = PSSH(pssh)

        # 處理 PSSH 驗證
        if not pssh:
            logger.error("Invalid PSSH: No WRM headers found")
            return None
        if len(pssh) < 76:
            # 這裡應該使用 logger.error 並返回 None 或 List[str]
            # 由於原始碼使用 raise ValueError，我們保留這個行為
            raise ValueError("Invalid PSSH: WRM header length is too short")

        # 定義 HTTP 請求頭
        headers: dict[str, str] = {
            "User-Agent": f"{CFG['headers']['User-Agent']}",
            "Connection": "Keep-Alive",
            "Content-Type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }

        # 獲取授權挑戰 (challenge 應為 bytes)
        challenge: bytes = self.cdm.get_license_challenge(self.session_id, req_pssh)

        # 異步 HTTP 請求
        async with httpx.AsyncClient(timeout=13.0, verify=True, http2=True) as client:
            response: httpx.Response = await client.post(
                url="https://berriz.drmkeyserver.com/widevine_license",
                headers=headers,
                data=challenge,
            )
            # 檢查 HTTP 狀態碼
            response.raise_for_status()

        # 解析授權內容
        self.cdm.parse_license(self.session_id, response.content)

        # 提取 Content Keys
        content_keys: list[str] = []
        # cdm.get_keys 返回一個 Key 列表 (pywidevine.cdm.key.Key)
        for key in self.cdm.get_keys(self.session_id):
            if key.type == "CONTENT":
                kid: str = key.kid.hex  # key.kid.hex 返回 str
                kid_str: str = str(kid) if isinstance(kid, bytes) else str(kid)
                kid_str = kid_str.replace("-", "")

                value: str | bytes = key.key.hex() if hasattr(key.key, "hex") else str(key.key)
                value_str: str = str(value) if isinstance(value, bytes) else str(value)

                content_keys.append(f"{kid_str}:{value_str}")

        # 關閉 session
        self.cdm.close(self.session_id)

        return content_keys
