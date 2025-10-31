import http.cookiejar
import sys
import time
from http.cookiejar import MozillaCookieJar
from pathlib import Path

from static.route import Route
from unit.handle.handle_log import setup_logging

route = Route()
DEFAULT_COOKIE: Path = route.default_cookie
cj = http.cookiejar.MozillaCookieJar(DEFAULT_COOKIE)


logger = setup_logging("loadcookie", "sunrise")


try:
    cj.load(ignore_discard=True, ignore_expires=True)
except FileNotFoundError:
    pass
except http.cookiejar.LoadError as e:
    if "does not look like a Netscape format cookies file" in str(e):
        logger.warning(f"Cookie file {DEFAULT_COOKIE} is not a Netscape format cookies file")
    else:
        raise http.cookiejar.LoadError(f"Error while loading cookie: {e}")


class LoadCookie:
    def __init__(self):
        self.file_path = DEFAULT_COOKIE
        self.domain = ".berriz.in"
        self.path = "/"
        self.cj = http.cookiejar.MozillaCookieJar(str(self.file_path))
        self._ensure_cookie_file()

        try:
            self.cj.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            sys.exit(1)

        self.cookie_bz_r = self._get_or_create_cookie("bz_r", "")
        self.cookie_bz_a = self._get_or_create_cookie("bz_a", "")

    def _ensure_cookie_file(self):
        """確保 cookie 檔案與資料夾存在"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.touch()
            self.cj.save()
            self.cj.load(ignore_discard=True, ignore_expires=True)

    def _get_or_create_cookie(self, name, default_value):
        try:
            return self.cj._cookies[self.domain][self.path][name]
        except KeyError:
            cookie = http.cookiejar.Cookie(
                version=0,
                name=name,
                value=default_value,
                port=None,
                port_specified=False,
                domain=self.domain,
                domain_specified=True,
                domain_initial_dot=True,
                path=self.path,
                path_specified=True,
                secure=False,
                expires=int(time.time()) + 3600,
                discard=False,
                comment=None,
                comment_url=None,
                rest={},
            )
            self.cj.set_cookie(cookie)
            return cookie

    def update_cookie(self, name: str, value: str):
        cookie = self._get_or_create_cookie(name, value)
        cookie.value = value
        self.cj.set_cookie(cookie)

    def save(self):
        self.cj.save(ignore_discard=True, ignore_expires=True)

    def find_all_cookiejars(self) -> list[str]:
        invalid_filenames: list[str] = []
        path1: Path = Path.cwd() / "cookies" / "Berriz"
        path2: Path = Path.cwd() / "cookies"

        for path in [path1, path2]:
            for txt_file in path.glob("*.txt"):
                try:
                    jar = MozillaCookieJar(str(txt_file))
                    jar.load(ignore_discard=True, ignore_expires=True)
                    if txt_file.name != "default.txt":
                        invalid_filenames.append(txt_file)
                except Exception:
                    pass
        return invalid_filenames


loadcookie = LoadCookie()
