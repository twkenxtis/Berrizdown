import functools
import random


from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.path import Path
from berrizdown.static.color import Color
from berrizdown.static.route import Route
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("Proxy", "cerulean")


PROXY_FILE: Path = Route().Proxy_list
PROXY_LIST_SETTING = CFG["Proxy"]["use_proxy_list"]
PROXY_SETTING = CFG["Proxy"]["use_proxy"]


class Proxy:
    def choese_proxy():
        if PROXY_LIST_SETTING is True:
            return "LIST_PROXY"
        elif PROXY_LIST_SETTING is False:
            if PROXY_SETTING.lower() == "http":
                return "HTTP_PROXY"
            elif PROXY_SETTING.lower() == "https":
                return "HTTPS_PROXY"

    @classmethod
    @functools.lru_cache(maxsize=10)
    def _load_proxies(cls) -> list[str]:
        """Load proxy strings from proxy.txt (cached)."""
        match Proxy.choese_proxy():
            case "LIST_PROXY":
                if not PROXY_FILE.exists():
                    logger.error(f"{Color.fg('gold')}{PROXY_FILE} not found.{Color.reset()}")
                    raise FileNotFoundError(f"{PROXY_FILE!r} not found.")
                with open(PROXY_FILE, encoding="utf-8") as f:
                    lines = f.readlines()
                    return [line.strip() for line in lines if line.strip()]
            case "HTTP_PROXY":
                http: list[str] = CFG["Proxy"]["http"]
                return random.choice([http])
            case "HTTPS_PROXY":
                https: list[str] = CFG["Proxy"]["https"]
                return random.choice([https])

    @property
    def proxy(self) -> list[str]:
        """Return list of proxy strings."""
        return self._load_proxies()

    @classmethod
    def remove(cls, proxy_url: str) -> bool:
        """Remove a specific proxy from proxy.txt based on the input URL."""
        try:
            # Extract components from proxy URL
            clean_url = proxy_url.replace("http://", "").replace("https://", "")
            auth_part, ip_port_part = clean_url.split("@", 1)
            username, password = auth_part.split(":", 1)

            # Create target patterns (with and without comma)
            base_pattern = f"{ip_port_part}:{username}:{password}"
            patterns = [base_pattern, base_pattern + ","]

            # Read and filter proxies
            if not PROXY_FILE.exists():
                logger.error(f"Proxy file not found: {PROXY_FILE}")
                return False

            with open(PROXY_FILE, encoding="utf-8") as f:
                proxies = f.readlines()

            # Filter out target proxy
            new_proxies = [line for line in proxies if line.strip() not in patterns]

            if len(new_proxies) == len(proxies):
                logger.warning(f"Proxy not found: {base_pattern}")
                return False

            # Write back to file
            with open("w", encoding="utf-8") as f:
                f.writelines(new_proxies)

            # Clear cache
            cls._load_proxies.cache_clear()

            logger.info(f"Successfully removed proxy: {base_pattern}")
            return True
        except Exception as e:
            logger.error(f"Error removing proxy {proxy_url}: {e}")
            return False

    @classmethod
    def remove_by_components(cls, ip: str, port: str, username: str, password: str) -> bool:
        """Remove proxy by individual components."""
        return cls.remove(f"http://{username}:{password}@{ip}:{port}")
