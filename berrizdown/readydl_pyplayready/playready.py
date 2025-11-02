from functools import cached_property, lru_cache

import aiohttp

from readydl_pyplayready.pyplayready.cdm import Cdm
from readydl_pyplayready.pyplayready.device import Device
from readydl_pyplayready.pyplayready.system.pssh import PSSH
from unit.handle.handle_log import setup_logging

logger = setup_logging("playready", "graphite")


class PlayReadyDRM:
    def __init__(self, device_path: str) -> None:
        self.device: Device = Device.load(device_path)
        self.cdm: Cdm = Cdm.from_device(self.device)

    @cached_property
    def session_id(self) -> bytes:
        return self.cdm.open()
    
    @lru_cache(maxsize=1)
    def build_pr_headers(self, acquirelicenseassertion: str) -> dict[str, str]:
        return {
            "user-agent": "Berriz/20250912.1136 CFNetwork/1498.700.2 Darwin/23.6.0",
            "content-type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }
        
    def pr_pssh_checker(self, pssh: str) -> PSSH:
        pssh_obj: PSSH = PSSH(pssh)
        if not pssh_obj.wrm_headers:
            logger.error("Invalid PSSH: No WRM headers found")
            raise ValueError("Invalid PSSH: No WRM headers found")
        if len(pssh) < 76:
            raise ValueError("Invalid PSSH: WRM header length is too short")
        return pssh_obj

    async def get_license_key(self, pssh: str, acquirelicenseassertion: str) -> list[str] | None:
        try:
            pssh_obj: PSSH = self.pr_pssh_checker(pssh)
            challenge: bytes = self.cdm.get_license_challenge(self.session_id, pssh_obj.wrm_headers[0])
            headers: dict[str, str] = self.build_pr_headers(acquirelicenseassertion)

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=13.0),
                connector=aiohttp.TCPConnector(ssl=True),
            ) as client:
                async with client.post(
                    url="https://berriz.drmkeyserver.com/playready_license",
                    headers=headers,
                    data=challenge
                ) as response:
                    if response.status not in range(200, 299):
                        logger.error(f"Invalid response status code: {response.status} {await response.text()}")
                    else:
                        license_text = await response.text()
                        self.cdm.parse_license(self.session_id, license_text)
                        return self.parse_response_key()

        except Exception as e:
            logger.error(e)
            return None

        finally:
            self.cdm.close(self.session_id)

    def __enter__(self) -> "PlayReadyDRM":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cdm.close(self.session_id)
        
    def parse_response_key(self) -> list[str]:
        content_keys: list[str] = []
        keys: list = self.cdm.get_keys(self.session_id)
        for key in keys:
            kid: str = key.key_id.hex() if isinstance(key.key_id, bytes) else str(key.key_id)
            kid = kid.replace("-", "")
            value: str = key.key.hex() if isinstance(key.key, bytes) else str(key.key)
            content_keys.append(f"{kid}:{value}")
        return content_keys
