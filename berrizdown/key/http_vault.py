from typing import Any

import httpx

from berrizdown.lib.load_yaml_config import CFG
from berrizdown.static.color import Color
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("http_vault", "apple_green")


# ENV_PATH: str = Path(__file__).parent.parent.joinpath('static', '.env')
# load_dotenv(dotenv_path=ENV_PATH)

# try:
#     # API Key if need
#     api = os.getenv('')
# except Exception as e:
#     logger.error(e)
#     raise ValueError("api Failed to load") from e


class HTTP_API:
    URL = CFG["remote_cdm"][-1]["host"]

    logger.info(f"HTTP_API URL: {URL}")

    def __init__(self) -> None:
        pass

    def get_license_url(self, pssh: str) -> str | None:
        match len(pssh):
            case 76:
                return "https://berriz.drmkeyserver.com/widevine_license"
            case _:
                return "https://berriz.drmkeyserver.com/playready_license"

    async def get_license_key(self, pssh: tuple[str, str], assertion: str) -> list[str] | None:
        wv_pssh: str = pssh[0]
        playready_pssh: str = pssh[1]

        url = HTTP_API.URL or "None"
        license_url: str | None = self.get_license_url(wv_pssh or playready_pssh)
        headers: dict[str, str] = {
            "accept": "application/json, text/plain, */*",
            # acquirelicenseassertion is berriz private token required to get license key
            "acquirelicenseassertion": assertion,
        }
        json_data: dict[str, Any] = {
            "pssh": wv_pssh or playready_pssh,
            "licurl": license_url,
            "headers": str(headers),
        }
        headers = {"content-type": "application/json"}
        if license_url is None:
            raise ValueError("Invalid licurl")
        if "http" in url and len(url) > 0:
            return await self.send_http_request(url, json_data, headers)
        else:
            logger.error(f"Failed to get license key: Invalid HTTP Vault URL, Empty or Invalid URL: {url}")
            return []

    async def send_http_request(self, url: str, json_data: dict[str, Any], headers: dict[str, str]) -> list[str]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=json_data,
                headers=headers,
            )
        if response.status_code != 200:
            logger.error(f"Failed to get license key: {response.status_code} {response.text}")
            return []

        # logger.debug(response, response.json(), response.headers, response.content, response.status_code)

        return self.key_handler(response)

    def key_handler(self, response: httpx.Response) -> list[str]:
        keys: list[str] = []
        logger.info(f"HTTP_API response: {response.json()}")
        resp = response.json().get("message", "").strip()
        if resp == "":
            logger.error(
                f"Failed to parse response got empty! Use:{Color.reset()}"
                f"{Color.fg('yellow')} response.json().get('message', '').strip(){Color.reset()}"
                f"{Color.fg('white')} Check HTTP API response for more information{Color.reset()}"
            )
            return []
        keys.append(resp)
        return keys
