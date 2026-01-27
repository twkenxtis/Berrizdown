import aiohttp

from berrizdown.lib.load_yaml_config import CFG
from berrizdown.readydl_pyplayready.pyplayready.remote import remotecdm
from berrizdown.readydl_pyplayready.pyplayready.system.pssh import PSSH
from berrizdown.unit.__init__ import USERAGENT
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("remotecdm_pr", "turquoise")


class Remotecdm_Playready:
    def __init__(self) -> None:
        self.url = "https://berriz.drmkeyserver.com/playready_license"

    def get_config(self):
        for config in CFG["remote_cdm"]:
            if config["name"] == "playready":
                return config

    def get_rcdm(self) -> remotecdm:
        CF: dict[str, int] = self.get_config()
        rcdm = remotecdm.RemoteCdm(
            security_level=int(CF["security_level"]),
            host=str(CF["host"]),
            secret=str(CF["secret"]),
            device_name=str(CF["device_name"]),
        )
        return rcdm

    def get_pssh(self, pssh_input: str) -> PSSH:
        if pssh_input is None or len(pssh_input) <= 300:
            raise ValueError("Invalid PSSH")
        else:
            pssh = PSSH(pssh_input)
            return pssh
        
    def build_headers(self, acquirelicenseassertion: str):
        return {
            "user-agent": USERAGENT,
            "content-type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }

    async def make_request_data(self, rcdm: remotecdm.RemoteCdm, session_id: bytes, pssh_input: str) -> str:
        pssh: PSSH = self.get_pssh(pssh_input)
        request_data: str = await rcdm.get_license_challenge(session_id, pssh.wrm_headers[0])
        return request_data

    async def get_license_key(self, pssh_input: str, acquirelicenseassertion: str) -> list[str]:
        rcdm: remotecdm = self.get_rcdm()
        session_id: bytes = await rcdm.open()
        
        if session_id == b"":
            return []
        
        headers: dict[str, str] = self.build_headers(acquirelicenseassertion)
        request_data: str = await self.make_request_data(rcdm, session_id, pssh_input)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=13.0),
            connector=aiohttp.TCPConnector(ssl=True)
            ) as session:   
            async with session.post(self.url, headers=headers, data=request_data) as response:
                if response.status != 200:
                    raise Exception("Error getting license key")
                license_response = await response.text()
        await rcdm.parse_license(session_id, license_response)
        return await self.parse_response_key(rcdm, session_id)

    async def parse_response_key(self, rcdm: remotecdm.RemoteCdm, session_id: bytes):
        key_list: list[str] = []
        for key in await rcdm.get_keys(session_id):
            key_list.append(f"{key.key_id.hex}:{key.key.hex()}")
        await rcdm.close(session_id)
        return key_list
