from urllib.parse import urlparse


from berrizdown.lib.load_yaml_config import CFG
from berrizdown.lib.path import Path
from berrizdown.unit.__init__ import FilenameSanitizer
from berrizdown.unit.date.date import get_timestamp_formact

fmt_files: str = get_timestamp_formact(CFG["output_template"]["date_formact"])
fmt_dir: str = get_timestamp_formact(CFG["donwload_dir_name"]["date_formact"])


def get_image_ext_basename(image_url: str) -> tuple[str, str]:
    if isinstance(image_url, str) and image_url.lower().startswith(("http://", "https://")):
        base_name: str = Path(urlparse(image_url).path).stem
        ext: str = Path(urlparse(image_url).path).suffix
        return base_name, ext
    raise ValueError(f"Invalid image_url: {image_url}")


def _require_str(name: str, value: str | None) -> str:
    if value is None:
        raise ValueError(f"{name} must not be None")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a str, got {type(value).__name__}")
    if value.strip() == "":
        raise ValueError(f"{name} must not be empty or whitespace")
    return value


def meta_name(
    time_str: str | None,
    title: str | None,
    community_name: str | None,
    artist_name: str | None = None,
) -> dict[str, str]:
    if time_str is None:
        raise ValueError("time_str must not be None")
    if title is None:
        raise ValueError("title must not be None")
    if community_name is None:
        raise ValueError("community_name must not be None")
    if artist_name is None:
        raise ValueError("artist_name must not be None")
    time_str = _require_str("time_str", time_str)
    if isinstance(title, str) and title.strip() == "":
        title: str = "NoTitle"
    title = _require_str("title", title)
    if isinstance(community_name, str) and community_name.strip() == "":
        community_name: str = "NoCommunityname"
    community_name = _require_str("community_name", community_name)
    if isinstance(artist_name, str) and artist_name.strip() == "":
        artist_name: str = "UnknownArtistname"
    artist_name = _require_str("artist", artist_name)
    if artist_name == community_name:
        artist_name = artist_name.lower()

    meta: dict[str, str] = {
        "date": time_str,
        "title": FilenameSanitizer.sanitize_filename(title),
        "community_name": community_name,
        "artis": artist_name,
        "source": "Berriz",
        "tag": CFG["output_template"]["tag"],
    }
    return meta
