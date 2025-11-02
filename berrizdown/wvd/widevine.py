import aiohttp
from functools import cached_property, lru_cache
from wvd.pywidevine.cdm import Cdm
from wvd.pywidevine.device import Device
from wvd.pywidevine.pssh import PSSH
from unit.handle.handle_log import setup_logging

logger = setup_logging("widevine", "navy")


class WidevineDRM:
    device: Device
    cdm: Cdm
    session_id: bytes

    def __init__(self, device_path: str) -> None:
        self.device: Device = Device.load(device_path)
        self.cdm: Cdm = Cdm.from_device(self.device)
    
    @cached_property
    def session_id(self) -> bytes:
        return self.cdm.open()
    
    @lru_cache(maxsize=1)
    def build_wv_headers(self, acquirelicenseassertion: str) -> dict[str, str]:
        return {
            "user-agent": "Berriz/20250912.1136 CFNetwork/1498.700.2 Darwin/23.6.0",
            "content-type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }
        
    def wv_pssh_checker(self, pssh: str) -> PSSH:
        req_pssh: PSSH = PSSH(pssh)
        if not pssh:
            logger.error("Invalid PSSH: No WRM headers found")
            raise ValueError("Invalid PSSH: No WRM headers found")
        if len(pssh) < 76:
            raise ValueError("Invalid PSSH: WRM header length is too short")
        return req_pssh

    async def get_license_key(self, pssh: str, acquirelicenseassertion: str) -> list[str] | None:
        try:
            req_pssh: PSSH = self.wv_pssh_checker(pssh)
            challenge: bytes = self.cdm.get_license_challenge(self.session_id, req_pssh)
            headers: dict[str, str] = self.build_wv_headers(acquirelicenseassertion)

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=13.0),
                connector=aiohttp.TCPConnector(ssl=True)
                ) as client:
                async with client.post(
                    url="https://berriz.drmkeyserver.com/widevine_license",
                    headers=headers,
                    data=challenge,
                ) as response:
                    if response.status not in range(200, 299):
                            logger.error(f"Invalid response status code: {response.status} {await response.read()}")
                    else:
                        license_content: bytes = await response.read()
                        self.cdm.parse_license(self.session_id, license_content)
                        return self.parse_response_key()
        except Exception as e:
            logger.error(e)
            return None
            
        finally:
            self.cdm.close(self.session_id)
            
    def __enter__(self) -> "WidevineDRM":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cdm.close(self.session_id)
    
    def parse_response_key(self) -> list[str]:
        content_keys: list[str] = []
        for key in self.cdm.get_keys(self.session_id):
            if key.type == "CONTENT":
                kid: str = key.kid.hex
                kid_str: str = str(kid) if isinstance(kid, bytes) else str(kid)
                kid_str = kid_str.replace("-", "")
                value: str | bytes = key.key.hex() if hasattr(key.key, "hex") else str(key.key)
                value_str: str = str(value) if isinstance(value, bytes) else str(value)
                content_keys.append(f"{kid_str}:{value_str}")
        return content_keys
