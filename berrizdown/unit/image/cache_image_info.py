from functools import lru_cache
from typing import Any

from unit.image.parse_public_contexts import IMG_PublicContext


class CachePublicINFO:
    def __init__(self, IMG_Publicinfo: IMG_PublicContext, default_community_name: str):
        self.IMG_Publicinfo: IMG_PublicContext = IMG_Publicinfo
        self._default_name: str = default_community_name

    @property
    @lru_cache(maxsize=1)
    def community_name(self) -> str:
        custom_cm_name = self.IMG_Publicinfo.community_name
        if custom_cm_name is None:
            return self._default_name
        return custom_cm_name

    @property
    @lru_cache(maxsize=1)
    def published_at(self) -> Any | None:
        return self.IMG_Publicinfo.published_at

    @property
    @lru_cache(maxsize=1)
    def title(self) -> Any | None:
        return self.IMG_Publicinfo.title

    @property
    @lru_cache(maxsize=1)
    def media_id(self) -> Any | None:
        return self.IMG_Publicinfo.media_id
