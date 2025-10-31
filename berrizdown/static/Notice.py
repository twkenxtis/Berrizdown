import warnings
from typing import Any, cast

from pydantic import BaseModel, Field

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

ID = int | str
DictAny = dict[str, Any]
RawNoticeItem = dict[str, ID | str | None]


class PydanticNoticeItem(BaseModel):
    """單一公告內容的 Pydantic 模型 (用於內容列表)"""

    community_notice_id: ID | None = Field(None, alias="communityNoticeId")
    title: str | None = None
    reserved_at: str | None = Field(None, alias="reservedAt")


class NoticeCursor(BaseModel):
    """分頁遊標資訊"""

    cursor_next: ID | None = Field(None, alias="next")


class NoticeData(BaseModel):
    """Notice API 響應中的 data 容器"""

    cursor: NoticeCursor = Field(default_factory=NoticeCursor)
    has_next: bool | None = Field(None, alias="hasNext")
    contents: list[PydanticNoticeItem] = Field(default_factory=list)


class NoticePayload(BaseModel):
    """Notice API 響應的頂層結構"""

    code: ID | None = None
    message: str | None = None
    data: NoticeData = Field(default_factory=NoticeData)


class Notice:
    # root
    code: ID | None
    message: str | None

    cursor_next: ID | None
    has_next: bool | None

    notices: list[RawNoticeItem]

    # fields
    by_id: dict[ID, RawNoticeItem]
    sorted_by_time: list[RawNoticeItem]
    sorted_desc_time: list[RawNoticeItem]
    first: RawNoticeItem | None
    last: RawNoticeItem | None

    def __init__(self, payload: Any) -> None:
        try:
            validated = NoticePayload.model_validate(payload)
        except Exception:
            validated = NoticePayload(code=payload.get("code"), message=payload.get("message"))

        data = validated.data
        cursor = data.cursor

        # Root
        self.code = validated.code
        self.message = validated.message

        # Cursor info
        self.cursor_next = cursor.cursor_next

        # Pagination flag
        self.has_next = data.has_next

        # Normalized notices: 保留原始 JSON 鍵名
        self.notices: list[RawNoticeItem] = []
        for item in data.contents:
            # 從 Pydantic 模型轉換回原始字典鍵名 (CamelCase)
            self.notices.append(
                {
                    "communityNoticeId": item.community_notice_id,
                    "title": item.title,
                    "reservedAt": item.reserved_at,
                }
            )

        # Convenience indexes and maps
        # By ID
        self.by_id: dict[ID, RawNoticeItem] = {cast(ID, n["communityNoticeId"]): n for n in self.notices if n.get("communityNoticeId") is not None}
        # 排序邏輯
        self.sorted_by_time: list[RawNoticeItem] = sorted(
            self.notices,
            key=lambda n: (n.get("reservedAt") is None, n.get("reservedAt")),
        )
        # Most recent first
        self.sorted_desc_time: list[RawNoticeItem] = list(reversed(self.sorted_by_time))

        # Lightweight helpers
        self.first: RawNoticeItem | None = self.sorted_by_time[0] if self.sorted_by_time else None
        self.last: RawNoticeItem | None = self.sorted_desc_time[0] if self.sorted_desc_time else None


class CommunityNotice(BaseModel):
    """單一公告詳情的核心內容"""

    community_notice_id: ID | None = Field(None, alias="communityNoticeId")
    title: str | None = None
    body: str | None = None
    event_id: ID | None = Field(None, alias="eventId")
    reserved_at: str | None = Field(None, alias="reservedAt")


class NoticeInfoData(BaseModel):
    """Notice Info API 響應中的 data 容器"""

    community_notice: CommunityNotice = Field(default_factory=CommunityNotice, alias="communityNotice")


class NoticeInfoPayload(BaseModel):
    """Notice Info API 響應的頂層結構"""

    code: ID | None = None
    message: str | None = None
    data: NoticeInfoData = Field(default_factory=NoticeInfoData)


class Notice_info:
    # root
    code: ID | None
    message: str | None

    # content
    communityNoticeId: ID | None
    title: str | None
    body: str | None
    eventId: ID | None
    reservedAt: str | None

    def __init__(self, payload: Any) -> None:
        try:
            validated = NoticeInfoPayload.model_validate(payload)
        except Exception:
            validated = NoticeInfoPayload(code=payload.get("code"), message=payload.get("message"))

        community_notice = validated.data.community_notice

        # Root
        self.code = validated.code
        self.message = validated.message

        # info
        self.communityNoticeId = community_notice.community_notice_id
        self.title = community_notice.title
        self.body = community_notice.body
        self.eventId = community_notice.event_id
        self.reservedAt = community_notice.reserved_at
