import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lib.__init__ import use_proxy
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Notify

logger = setup_logging("GetMediaList", "turquoise")


class NotifyFetcher:
    def __init__(self):
        self.json_data: dict[str, Any] | None = None
        self.Notify = Notify()

    async def get_all_notify_lists(self, time_a: datetime | None, time_b: datetime | None) -> list[dict[str, Any]] | None:
        params: dict[str, Any] = {"pageSize": 100, "languageCode": "en"}
        all_contents: list[dict[str, Any]] = []

        while True:
            self.json_data = await self._fetch_data(params)
            if not self.json_data:
                break

            contents, params, hasNext = await self.basic_sort_josn()
            all_contents.extend(contents)
            if hasNext is False:
                live_list: list[dict[str, Any]] = await Process_Notify(all_contents)._extract_media_items(time_a, time_b)
                return live_list
        return None

    async def _fetch_data(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self.Notify.fetch_notify("", params, use_proxy)

    async def basic_sort_josn(
        self,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        if self.json_data and self.json_data.get("code") == "0000":
            cursor: dict[str, Any] = self.json_data.get("data").get("cursor")
            hasNext: bool = self.json_data.get("data").get("hasNext")
            contents: list[dict[str, Any]] = self.json_data.get("data").get("contents")
            params: dict[str, Any] = await self.build_params(cursor)
            return contents, params, hasNext
        # Fallbacks to satisfy typing, though code path expects '0000'
        return [], {"pageSize": 100, "languageCode": "en"}, False

    async def build_params(self, cursor: dict[str, Any] | None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageSize": 100, "languageCode": "en"}
        if cursor:
            next_int: Any = cursor["next"]
            params["next"] = next_int
        return params


@dataclass
class Notification:
    id: str
    notificationType: str
    communityId: str
    communityKey: str
    isCommunityNotification: bool
    message: str
    messageByType: dict[str, str]
    senderName: str
    senderImageUrl: str
    publishedAt: str
    linkUrl: str
    additionalInfo: dict[str, Any]
    isFanclubOnly: bool
    imageUrl: str
    imageCount: int
    notificationCase: str
    imageMetadata: dict[str, Any]

    def _parse_message(self) -> tuple[str, str, str]:
        return (
            self.messageByType.get("title", ""),
            self.messageByType.get("context", ""),
            self.messageByType.get("message", ""),
        )


def NCA001(note: Notification) -> None:
    pass


def NCA002(note: Notification) -> None:
    pass


class NCA005(Notification):
    def __init__(self, note: Notification):
        super().__init__(**note.__dict__)
        self.title, self.context, self.message = self._parse_message()
        self.source_artist, self.media_id, self.media_type, self.liveStatus = self._parse_additional_info()

    def _parse_additional_info(self) -> tuple[str, str, str | bool, str]:
        info: dict[str, Any] = self.additionalInfo.get("notificationInfo", {})
        return (
            info.get("sourceArtist", ""),
            info.get("liveId", ""),
            info.get("mediaType", False),
            info.get("liveStatus", ""),
        )


def NCA009(note: Notification) -> None:
    pass


def NCA010(note: Notification) -> None:
    pass


class NCA011(Notification):
    def __init__(self, note: Notification):
        super().__init__(**note.__dict__)
        self.title, self.context, self.message = self._parse_message()
        (
            self.context,
            self.sourceArtist,
            self.media_id,
            self.mediaType,
            self.isFanclubOnly,
            self.liveStatus,
        ) = self._parse_additional_info()

    def _parse_additional_info(self) -> tuple[str, str, str, str, bool, str]:
        info: dict[str, Any] = self.additionalInfo.get("notificationInfo", {})
        return (
            info.get("context", ""),
            info.get("sourceArtist", ""),
            info.get("mediaId", ""),
            info.get("mediaType", ""),
            info.get("isFanclubOnly", False),
            info.get("liveStatus", ""),
        )


def NCA015(note: Notification) -> None:
    pass


def NCA101(note: Notification) -> None:
    pass


def Other_NCA(note: Notification) -> None:
    pass


# Handler can be either:
# - a function taking Notification and returning Any (sync or async), or
# - a class that can be instantiated with Notification (e.g., NCA005/NCA011)
HandlerType = Callable[[Notification], Any] | Callable[[Notification], Awaitable[Any]] | type

HANDLERS: dict[str, HandlerType] = {
    "NCA001": NCA001,
    "NCA002": NCA002,
    "NCA005": NCA005,  # class
    "NCA009": NCA009,
    "NCA010": NCA010,
    "NCA011": NCA011,  # class
    "NCA015": NCA015,
    "NCA101": NCA101,
}


class Process_Notify:
    def __init__(self, contents: list[dict[str, Any]]):
        self.contents: list[dict[str, Any]] = contents

    async def unpack_contents(self) -> Any:
        for item in self.contents:
            yield Notification(**item)

    async def match(self) -> Any:
        async for note in self.unpack_contents():
            handler: HandlerType = HANDLERS.get(note.notificationCase, Other_NCA)
            if inspect.isclass(handler):
                yield handler(note)
            elif inspect.iscoroutinefunction(handler):  # async function handler
                yield await handler(note)
            else:  # regular function handler
                yield handler(note)

    async def _extract_media_items(self, time_a: datetime | None = None, time_b: datetime | None = None) -> list[dict[str, Any]]:
        live_list: list[dict[str, Any]] = []
        # 檢查是否需要進行時間篩選 -> bool
        should_filter_by_time: bool = isinstance(time_a, datetime) and isinstance(time_b, datetime)
        # 確保時間範圍順序正確
        if should_filter_by_time and time_a and time_b and time_a > time_b:
            time_a, time_b = time_b, time_a
        async for h in self.match():
            if isinstance(h, (NCA005, NCA011)):
                media: dict[str, Any] = {
                    "mediaId": h.media_id,
                    "mediaType": "LIVE",
                    "title": h.context,
                    "thumbnailUrl": h.imageUrl,
                    "publishedAt": h.publishedAt,
                    "communityId": h.communityId,
                    "isFanclubOnly": h.publishedAt,
                    "live": h.liveStatus,
                }
                published_at_str: str | None = h.publishedAt
                # 進行時間範圍篩選
                if should_filter_by_time and published_at_str and time_a and time_b:
                    try:
                        # 將字串轉換為 datetime 物件，並處理時區
                        published_at: datetime = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        if not (time_a <= published_at <= time_b):
                            continue
                    except (ValueError, TypeError):
                        continue
                live_list.append(media)
        return live_list
