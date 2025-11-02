import os
import re
import urllib.parse
from re import Pattern

URI_PATTERN: Pattern[str] = re.compile(r'URI="([^"]+)"')


async def rebuild_master_playlist(m3u8: str, m3u8_uri: str) -> str:
    # m3u8 是一個包含 .text 屬性的物件
    parsed_url: urllib.parse.ParseResult = urllib.parse.urlparse(m3u8_uri)
    base_url: str = f"{parsed_url.scheme}://{parsed_url.netloc}{os.path.dirname(parsed_url.path)}/"

    lines: list[str] = m3u8.strip().split("\n")
    rebuilt_lines: list[str] = []

    for line_raw in lines:
        line: str = line_raw.strip()
        if not line:
            continue

        # 檢查是否是 URI 行（不以 # 開頭的行）
        if not line.startswith("#"):
            # 這是 URI 行，需要更新 URL
            new_uri: str = urllib.parse.urljoin(base_url, line)
            rebuilt_lines.append(new_uri)
        else:
            # 檢查是否是包含 URI 的 EXT-X-MEDIA 行
            if line.startswith("#EXT-X-MEDIA:") and "URI=" in line:
                uri_match: re.Match[str] | None = URI_PATTERN.search(line)
                if uri_match:
                    old_uri: str = uri_match.group(1)
                    new_uri: str = urllib.parse.urljoin(base_url, old_uri)
                    line = line.replace(f'URI="{old_uri}"', f'URI="{new_uri}"')
            rebuilt_lines.append(line)
    return "\n".join(rebuilt_lines)
