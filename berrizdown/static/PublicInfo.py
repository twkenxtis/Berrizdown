from typing import Any
from uuid import UUID

import orjson
from lib.load_yaml_config import CFG
from pydantic import BaseModel, Field, model_validator
from unit.date.date import get_formatted_publish_date


class MediaArtistModel(BaseModel):
    """artis info"""

    community_artist_id: int | None = Field(None, alias="communityArtistId")
    name: str | None = None
    image_url: str | None = Field(None, alias="imageUrl")


class MediaCategoryModel(BaseModel):
    """like Tag"""

    media_category_id: int | None = Field(None, alias="mediaCategoryId")
    media_category_name: str | None = Field(None, alias="mediaCategoryName")


class MediaDataModel(BaseModel):
    """all media data"""

    media_seq: int | None = Field(None, alias="mediaSeq")
    media_id: UUID | None = Field(None, alias="mediaId")
    media_type: str | None = Field(None, alias="mediaType")
    title: str | None = None
    body: str | None = None
    thumbnail_url: str | None = Field(None, alias="thumbnailUrl")
    published_at: str | None = Field(None, alias="publishedAt")
    community_id: int | None = Field(None, alias="communityId")
    is_fanclub_only: bool | None = Field(None, alias="isFanclubOnly")


class CommentDataModel(BaseModel):
    """comment"""

    content_type_code: str | None = Field(None, alias="contentTypeCode")
    read_content_id: str | None = Field(None, alias="readContentId")
    write_content_id: str | None = Field(None, alias="writeContentId")


class PublicAPIDataModel(BaseModel):
    """Data"""

    media: MediaDataModel = Field(default_factory=MediaDataModel)
    community_artists: list[MediaArtistModel] = Field(default_factory=list, alias="communityArtists")
    media_categories: list[MediaCategoryModel] = Field(default_factory=list, alias="mediaCategories")
    comment: CommentDataModel = Field(default_factory=CommentDataModel)


class PublicPayloadModel(BaseModel):
    """PublicInfo API root info"""

    code: int | None = None
    message: str | None = None
    data: PublicAPIDataModel = Field(default_factory=PublicAPIDataModel)


class PublicInfo:
    code: int | None
    status: str | None
    data: dict
    media_data: dict
    media_seq: int | None
    media_id: UUID | None
    media_type: str | None
    title: str | None
    body: str | None
    thumbnail_url: str | None
    published_at: str | None
    community_id: int | None
    is_fanclub_only: bool | None
    artists: list[dict]
    artists_data: list[dict]
    categories: list[dict]
    comment_data: dict
    comment_info: dict

    def __init__(self, public_context: dict[str, Any] | tuple[Any, dict[str, Any]]):
        if isinstance(public_context, tuple):
            context_data = public_context[1]
        else:
            context_data = public_context

        validated: PublicPayloadModel = PublicPayloadModel.model_validate(context_data)

        # Top-level info
        self.code = validated.code
        self.status = validated.message

        self.data: dict = validated.data.model_dump(by_alias=True)
        self.media_data: dict = self.data.get("media", {})

        # Media data
        media = validated.data.media
        self.media_seq = media.media_seq
        self.media_id = media.media_id
        self.media_type = media.media_type
        self.title = media.title
        self.body = media.body
        self.thumbnail_url = media.thumbnail_url
        self.published_at = media.published_at
        self.community_id = media.community_id
        self.is_fanclub_only = media.is_fanclub_only

        # Artists
        self.artists_data: list[dict] = validated.data.model_dump(by_alias=True).get("communityArtists", [])
        self.artists: list[dict] = [{"id": a.community_artist_id, "name": a.name, "image_url": a.image_url} for a in validated.data.community_artists]

        # Categories
        self.categories: list[dict] = [{"id": c.media_category_id, "name": c.media_category_name} for c in validated.data.media_categories]

        # Comment info
        comment = validated.data.comment
        self.comment_data: dict = validated.data.model_dump(by_alias=True).get("comment", {})
        self.comment_info: dict = {
            "content_type": comment.content_type_code,
            "read_content_id": comment.read_content_id,
            "write_content_id": comment.write_content_id,
        }

    def get_primary_artist(self) -> dict | None:
        artist = self.artists[0] if self.artists else None
        return artist if artist else None

    def get_category_names(self) -> list[str]:
        return [cat["name"] for cat in self.categories if cat.get("name")]

    def __str__(self):
        return f"PublicInfo(media_id={self.media_id}, title={self.title}, artists={[a['name'] for a in self.artists]})"

    def to_dict(self):
        if str(self.code) != "0000":
            return {"error": "Invalid status code"}

        return {
            "code": self.code,
            "status": self.status,
            "media": {
                "seq": self.media_seq,
                "id": self.media_id,
                "type": self.media_type,
                "title": self.title,
                "published_at": self.published_at,
                "formatted_published_at": get_formatted_publish_date(self.published_at, CFG.config["output_template"]["date_formact"]),
                "community_id": self.community_id,
                "is_fanclub_only": self.is_fanclub_only,
                "thumbnail_url": self.thumbnail_url,
                "description": self.body,
            },
            "artists": self.artists,
            "categories": self.categories,
            "comment_info": self.comment_info,
        }

    def to_json(self):
        """Convert to JSON string with pretty formatting"""
        return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2).decode("utf-8")


class CustomMediaModel(BaseModel):
    """PublicInfo_Custom media"""

    seq: int | None
    id: str | None
    type: str | None
    title: str | None
    published_at: str | None
    formatted_published_at: str | None
    community_id: int | None
    is_fanclub_only: bool | None
    thumbnail_url: str | None
    description: str | None


class CustomArtistModel(BaseModel):
    """PublicInfo_Custom artis info"""

    id: str | None
    name: str | None
    image_url: str | None

    @model_validator(mode="before")
    @classmethod
    def convert_id_to_str(cls, data: Any) -> Any:
        if isinstance(data, dict) and "id" in data and data["id"] is not None:
            data["id"] = str(data["id"])
        return data


class CustomCommentInfoModel(BaseModel):
    """PublicInfo_Custom comment info"""

    content_type: str | None
    read_content_id: str | None
    write_content_id: str | None


class PublicCustomPayloadModel(BaseModel):
    """PublicInfo_Custom"""

    code: str | None = None
    status: str | None = None
    media: CustomMediaModel = Field(default_factory=CustomMediaModel)
    artists: list[CustomArtistModel] = Field(default_factory=list)
    comment_info: CustomCommentInfoModel = Field(default_factory=CustomCommentInfoModel, alias="comment_info")


class PublicInfo_Custom:
    code: str | None
    status: str | None
    media_seq: int | None
    media_id: str | None
    media_type: str | None
    media_title: str | None
    media_published_at: str | None
    formatted_published_at: str | None
    media_community_id: int | None
    media_is_fanclub_only: bool | None
    media_thumbnail_url: str | None
    media_description: str | None
    artist_list: list[dict[str, str | None]]
    comment_content_type: str | None
    comment_read_content_id: str | None
    comment_write_content_id: str | None

    def __init__(self, public_context: tuple[dict[str, Any]]):
        context_data = public_context[0]

        validated: PublicCustomPayloadModel = PublicCustomPayloadModel.model_validate(context_data)

        self.code = validated.code
        self.status = validated.status

        media = validated.media
        self.media_seq = media.seq
        self.media_id = media.id
        self.media_type = media.type
        self.media_title = media.title
        self.media_published_at = media.published_at
        self.formatted_published_at = media.formatted_published_at
        self.media_community_id = media.community_id
        self.media_is_fanclub_only = media.is_fanclub_only
        self.media_thumbnail_url = media.thumbnail_url
        self.media_description = media.description

        # Artists
        self.artist_list: list[dict[str, str | None]] = [{"id": artist.id, "name": artist.name, "image_url": artist.image_url} for artist in validated.artists]

        # Comment info
        comment_info = validated.comment_info
        self.comment_content_type = comment_info.content_type
        self.comment_read_content_id = comment_info.read_content_id
        self.comment_write_content_id = comment_info.write_content_id
