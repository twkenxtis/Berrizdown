from __future__ import annotations

import rich.traceback
from ruamel.yaml import YAML

from berrizdown.lib.path import Path

rich.traceback.install()

with open(
    Path(__file__).parent.parent.joinpath("berrizconfig.yaml"),
    encoding="utf-8",
) as f:
    CFG: dict = YAML().load(f.read())


class Route:
    def __init__(self):
        mainpath = Path(__file__)
        self.default_cookie: Path = mainpath.parent.parent.joinpath("cookies", "Berriz", "default.txt")
        self.DB_FILE: Path = mainpath.parent.parent.joinpath("key", "key_store.db")
        self.YAML_path: Path = mainpath.parent.parent.joinpath("berrizconfig.yaml")
        self.mp4decrypt_path: Path = mainpath.parent.parent.joinpath("lib", "tools", CFG["Container"]["mp4decrypt"])
        self.packager_path: Path = mainpath.parent.parent.joinpath("lib", "tools", CFG["Container"]["shaka-packager"])
        self.mkvmerge_path: Path = mainpath.parent.parent.joinpath("lib", "tools", CFG["Container"]["mkvmerge"])
        self.Proxy_list = mainpath.parent.parent.joinpath("static", "proxy", "proxy.txt")
        self.download_info_db = mainpath.parent.parent.joinpath("lock", "download_info.db")
        self.ffmpeg = mainpath.parent.parent.joinpath("lib", "tools", CFG["Container"]["ffmpeg"])
        self.ffprobe = mainpath.parent.parent.joinpath("lib", "tools", CFG["Container"]["ffprobe"])
