import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse


class URLExtractor:
    _url_pattern = re.compile(r"https?://.+?(?=\s|\||https?://|$)")
    _trailing_noise = re.compile(r'[.,;!?)"\']+$')

    def __init__(self, allowed_domains: tuple[str, ...] = ("berriz.in",)):
        self.allowed_domains = tuple(d.lower() for d in allowed_domains)
        self._last_result: tuple[str, ...] = ()

    def _flatten_data(self, item: Any) -> Iterator[str]:
        """使用遞迴生成器將複雜結構扁平化為單一字串序列"""
        if isinstance(item, dict):
            for value in item.values():
                yield from self._flatten_data(value)
        elif isinstance(item, (list, tuple, set)):
            for element in item:
                yield from self._flatten_data(element)
        else:
            yield str(item)

    def _is_valid_and_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        netloc_lower = parsed.netloc.lower()

        if parsed.scheme not in ("http", "https") or not netloc_lower:
            return False

        for allowed in self.allowed_domains:
            if netloc_lower == allowed or netloc_lower.endswith("." + allowed):
                return True
        return False

    def extract(self, data: Any) -> tuple[str, ...]:
        # 1. 扁平化資料並提取所有原始 URL
        #    - 使用列表推導式處理所有扁平化的字串
        #    - 使用 set 確保最終結果是唯一的原始 URL 集合
        raw_urls_generator = (raw_url for item_str in self._flatten_data(data) if isinstance(item_str, str) for raw_url in self._url_pattern.findall(item_str))

        unique_raw_urls = set(raw_urls_generator)

        result = tuple(cleaned for raw in unique_raw_urls if (cleaned := self._trailing_noise.sub("", raw)) and self._is_valid_and_allowed(cleaned))

        self._last_result = result
        return result

    def __call__(self, data: Any) -> tuple[str, ...]:
        return self.extract(data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._last_result)

    def __len__(self) -> int:
        return len(self._last_result)
