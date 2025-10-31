import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from lib.path import Path
from unit.handle.handle_log import setup_logging

logger = setup_logging("watora", "foggy")


ENV_PATH: Path = Path(__file__).parent.parent.joinpath("static", ".env")
load_dotenv(dotenv_path=ENV_PATH)

try:
    watora_api = os.getenv("watora_api")
except Exception as e:
    logger.error(e)
    raise ValueError("watora_api Failed to load") from e


class Watora_wv:
    def __init__(self) -> None:
        self.remote_cdm_api_key: str = str(watora_api)
        if self.remote_cdm_api_key is None:
            logger.error("watora_api is not set in static/.env")

    async def get_license_key(self, pssh: str, assertion: str) -> list[str] | None:
        _headers: dict[str, str] = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "acquirelicenseassertion": assertion,
        }
        json_data: dict[str, Any] = {
            "PSSH": pssh,
            "License URL": "https://berriz.drmkeyserver.com/widevine_license",
            "Headers": json.dumps(_headers),
            "Cookies": "{}",
            "Data": "{}",
            "Proxy": "",
            "JSON": {},
        }
        match len(self.remote_cdm_api_key):
            case 0:
                logger.error("Remote CDM API key is not set")
                return None
            case length if length >= 20:
                url = "https://cdm.watora.me"
                headers = {"Authorization": f"Bearer {self.remote_cdm_api_key}"}
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=json_data,
                        headers=headers,
                    )
                keys: list[str] = []
                keys.append(response.json().get("Message", "").strip())
                return keys
