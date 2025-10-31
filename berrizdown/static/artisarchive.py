import warnings
from typing import Any

import orjson
from pydantic import BaseModel, Field, model_validator

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


class BoardInfoModel(BaseModel):
    """BoardInfo"""

    board_id: str = Field("", alias="boardId")
    board_name: str = Field("", alias="boardName")
    is_fanclub_only: bool = Field(False, alias="isFanclubOnly")


class ReplyInfoModel(BaseModel):
    """Reply comment Info"""

    author_name: str | None = Field(None, alias="authorName")
    is_reply: bool = Field(False, alias="isReply")
    parent_comment_seq: int = Field(-1, alias="parentCommentSeq")


class ImageMetadataModel(BaseModel):
    """ImageMetadata"""

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def process_metadata(cls, value: Any) -> dict[str, Any]:
        """確保輸入是字典，並作為 metadata 的值"""
        if value is None:
            return {"metadata": {}}
        # 假設輸入就是 imageMetadata 的內容，它應該是一個 dict
        if isinstance(value, dict):
            return {"metadata": value}
        # 如果不是 dict 或 None，則用空字典初始化
        return {"metadata": {}}


class ArtistContentModel(BaseModel):
    post_id: str = Field("", alias="postId")
    user_id: int = Field(0, alias="userId")
    nickname: str = Field("", alias="userNickname")
    body: str = Field("", alias="body")
    created_at: str = Field("", alias="createdAt")
    profile_image_url: str = Field("", alias="profileImageUrl")
    content_type: str = Field("", alias="contentType")
    title: str | None = Field(None)
    image_url: str | None = Field(None, alias="imageUrl")
    image_count: int = Field(0, alias="imageCount")
    content_id: str = Field("", alias="contentId")
    is_parent_deleted: bool = Field(False, alias="isParentDeleted")

    board: BoardInfoModel = Field(default_factory=BoardInfoModel)
    reply_info: ReplyInfoModel = Field(default_factory=ReplyInfoModel, alias="replyInfo")
    image_metadata: ImageMetadataModel = Field(default_factory=ImageMetadataModel, alias="imageMetadata")


class ArtistContent:
    post_id: str
    user_id: int
    nickname: str
    body: str
    created_at: str
    profile_image_url: str
    content_type: str
    title: str | None
    image_url: str | None
    image_count: int
    content_id: str
    is_parent_deleted: bool

    board: BoardInfoModel
    reply_info: ReplyInfoModel
    image_metadata: ImageMetadataModel

    def __init__(self, data: dict[str, Any]) -> None:
        validated: ArtistContentModel = ArtistContentModel.model_validate(data)

        self.post_id = validated.post_id
        self.user_id = validated.user_id
        self.nickname = validated.nickname
        self.body = validated.body
        self.created_at = validated.created_at
        self.profile_image_url = validated.profile_image_url
        self.content_type = validated.content_type
        self.title = validated.title
        self.image_url = validated.image_url
        self.image_count = validated.image_count
        self.content_id = validated.content_id
        self.is_parent_deleted = validated.is_parent_deleted

        self.board = validated.board
        self.reply_info = validated.reply_info
        self.image_metadata = validated.image_metadata

    def __str__(self) -> str:
        return (
            f"[{self.content_type}] {self.nickname} ({self.created_at})\n"
            f"Body: {self.body}\n"
            f"Title: {self.title}\n"
            f"Images: {self.image_count} | URL: {self.image_url}\n"
            f"Board: {self.board.board_name} | Fanclub Only: {self.board.is_fanclub_only}\n"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert all data to dictionary, preserving original CamelCase keys."""
        return {
            "postId": self.post_id,
            "userId": self.user_id,
            "userNickname": self.nickname,
            "body": self.body,
            "createdAt": self.created_at,
            "profileImageUrl": self.profile_image_url,
            "contentType": self.content_type,
            "title": self.title,
            "imageUrl": self.image_url,
            "imageCount": self.image_count,
            "imageMetadata": self.image_metadata.metadata,
            "contentId": self.content_id,
            "isParentDeleted": self.is_parent_deleted,
            "board": self.board.model_dump(by_alias=True),
            "replyInfo": self.reply_info.model_dump(by_alias=True),
        }

    def to_son(self) -> bytes:
        """Convert to JSON bytes using orjson."""
        return orjson.dumps(self.to_dict())
