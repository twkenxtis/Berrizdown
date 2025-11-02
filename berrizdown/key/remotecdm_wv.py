import aiohttp

from lib.load_yaml_config import CFG
from lib.base64 import base64
from wvd.pywidevine.remotecdm import RemoteCdm
from wvd.pywidevine.pssh import PSSH
from wvd.pywidevine.device import DeviceTypes
from unit.__init__ import USERAGENT
from unit.handle.handle_log import setup_logging

logger = setup_logging("remotecdm_wv", "crimson")

class Remotecdm_Widevine:
    def __init__(self) -> None:
        self.url = "https://berriz.drmkeyserver.com/widevine_license"

    def get_config(self):
        for config in CFG["remote_cdm"]:
            if config["name"] == "widevine":
                return config

    def get_rcdm(self) -> RemoteCdm:
        CF: dict[str, int] = self.get_config()
        if CF["device_type"] is None:
            device_type = DeviceTypes.ANDROID
        elif str(CF["device_type"]) == "DeviceTypes.ANDROID":
            device_type = DeviceTypes.ANDROID
        else:
            device_type = CF["device_type"]

        rcdm = RemoteCdm(
            device_type=device_type,
            system_id=int(CF["system_id"]),
            security_level=int(CF["security_level"]),
            host=str(CF["host"]),
            secret=str(CF["secret"]),
            device_name=str(CF["device_name"]),
        )
        return rcdm

    def get_pssh(self, pssh_input: str) -> PSSH:
        if pssh_input is None or len(pssh_input) != 76:
            raise ValueError("Invalid PSSH")
        else:
            return PSSH(base64.b64decode(pssh_input))
        
    def build_headers(self, acquirelicenseassertion: str):
        return {
            "user-agent": USERAGENT,
            "content-type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }
        
    async def make_request_data(self, rcdm: RemoteCdm, session_id: bytes, pssh_input: str) -> str:
        pssh: PSSH = self.get_pssh(pssh_input)
        request_data: str = await rcdm.get_license_challenge(session_id, pssh.wrm_headers[0])
        return request_data

    async def get_license_key(self, pssh_input: str, acquirelicenseassertion: str) -> list[str]:
        rcdm: RemoteCdm = self.get_rcdm()
        session_id: bytes = await rcdm.open()
        
        if session_id == b"":
            return []
        
        headers: dict[str, str] = self.build_headers(acquirelicenseassertion)
        pssh: PSSH = self.get_pssh(pssh_input)
        challenge = await rcdm.get_license_challenge(session_id, pssh, "STREAMING", True)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=13.0),
            connector=aiohttp.TCPConnector(ssl=True)
            ) as session:
            async with session.post(self.url, headers=headers, data=challenge) as response:
                if response.status != 200:
                    raise Exception("Error getting license key")
                license_response = await response.read()
        await rcdm.parse_license(session_id, license_response)
        return await self.parse_response_key(rcdm, session_id)
        
    async def parse_response_key(self, rcdm: RemoteCdm, session_id: bytes) -> list[str]:
        key_list: list[str] = []
        for key in await rcdm.get_keys(session_id, "CONTENT"):
            key_list.append(f"{key.kid.hex}:{key.key.hex()}")
        await rcdm.close(session_id)
        return key_list