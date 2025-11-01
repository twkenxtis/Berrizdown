from functools import cached_property

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

    async def get_license_key(self, pssh: str, acquirelicenseassertion: str) -> list[str] | None:
        """
        使用 PSSH 與 acquirelicenseassertion 取得 PlayReady license key 列表

        :param pssh: Base64 或 Hex 編碼的 PSSH 字串
        :param acquirelicenseassertion: DRM 授權驗證字串
        :return: content key 列表或 None
        """
        try:
            pssh_obj: PSSH = PSSH(pssh)
            if not pssh_obj.wrm_headers:
                logger.error("Invalid PSSH: No WRM headers found")
                return None
            if len(pssh) < 76:
                raise ValueError("Invalid PSSH: WRM header length is too short")

            challenge: bytes = self.cdm.get_license_challenge(self.session_id, pssh_obj.wrm_headers[0])

            headers: dict[str, str] = {
                "user-agent": "Berriz/20250912.1136 CFNetwork/1498.700.2 Darwin/23.6.0",
                "content-type": "application/octet-stream",
                "acquirelicenseassertion": acquirelicenseassertion,
            }

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

                keys: list = self.cdm.get_keys(self.session_id)
                content_keys: list[str] = []
                for key in keys:
                    kid: str = key.key_id.hex() if isinstance(key.key_id, bytes) else str(key.key_id)
                    kid = kid.replace("-", "")
                    value: str = key.key.hex() if isinstance(key.key, bytes) else str(key.key)
                    content_keys.append(f"{kid}:{value}")
                return content_keys

        except Exception as e:
            logger.error(e)
            return None

        finally:
            self.cdm.close(self.session_id)

    def __enter__(self) -> "PlayReadyDRM":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cdm.close(self.session_id)
