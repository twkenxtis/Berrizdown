from typing import Any, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field


class PhotoDict(TypedDict, total=False):
    media_id: UUID | None
    image_url: str | None
    width: int | None
    height: int | None
    published_at: int | None


LinkDict = dict[str, Any]


class AnalysisDict(TypedDict, total=False):
    """no idea what this is"""

    media_id: UUID | None
    description: str | None


Hashtag = dict[str | int, Any]


class ImageMetadata(BaseModel):
    """image info list[2]"""

    width: int | None = None
    height: int | None = None
    published_at: int | None = Field(None, alias="publishedAt")


class Photo(BaseModel):
    """Single photo"""

    media_id: UUID | None = Field(None, alias="mediaId")
    image_url: str | None = Field(None, alias="imageUrl")
    image_metadata: ImageMetadata | None = Field(None, alias="imageMetadata")


class Link(BaseModel):
    pass


class Analysis(BaseModel):
    """AI Beta"""

    media_id: UUID | None = Field(None, alias="mediaId")
    description: str | None = None


class PostMedia(BaseModel):
    """POST MEDIA"""

    photo: list[Photo] = Field(default_factory=list)
    link: list[LinkDict] = Field(default_factory=list)
    analysis: list[Analysis] = Field(default_factory=list)


class PostModel(BaseModel):
    """Post"""

    post_id: UUID | None = Field(None, alias="postId")
    post_user_id: int | None = Field(None, alias="userId")
    post_community_id: int | None = Field(None, alias="communityId")
    title: str | None = None
    body: str | None = None
    plain_body: str | None = Field(None, alias="plainBody")
    language_code: str | None = Field(None, alias="languageCode")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    is_active: bool | None = Field(None, alias="isActive")
    is_baned: bool | None = Field(None, alias="isBaned")
    status: str | None = None
    is_updated: bool | None = Field(None, alias="isUpdated")
    media: PostMedia = Field(default_factory=PostMedia)
    hashtags: list[Hashtag] = Field(default_factory=list)


class WriterModel(BaseModel):
    """Writer"""

    writer_user_id: int | None = Field(None, alias="userId")
    writer_community_id: int | None = Field(None, alias="communityId")
    writer_type: str | None = Field(None, alias="type")
    writer_community_artist_id: int | None = Field(None, alias="communityArtistId")
    writer_is_artist: bool | None = Field(None, alias="isArtist")
    writer_name: str | None = Field(None, alias="name")
    writer_image_url: str | None = Field(None, alias="imageUrl")
    writer_bg_image_url: str | None = Field(None, alias="bgImageUrl")
    writer_is_fanclub_user: bool | None = Field(None, alias="isFanclubUser")


class CountInfoModel(BaseModel):
    """CountInfo"""

    comment_count: int | None = Field(None, alias="commentCount")
    like_count: int | None = Field(None, alias="likeCount")


class CommentInfoModel(BaseModel):
    """Comment"""

    content_type_code: int | None = Field(None, alias="contentTypeCode")
    read_content_id: str | None = Field(None, alias="readContentId")
    write_content_id: str | None = Field(None, alias="writeContentId")


class BoardInfoModel(BaseModel):
    """BoardInfo"""

    board_id: UUID | None = Field(None, alias="boardId")
    board_type: str | None = Field(None, alias="boardType")
    board_community_id: int | None = Field(None, alias="communityId")
    board_name: str | None = Field(None, alias="name")
    board_is_fanclub_only: bool | None = Field(None, alias="isFanclubOnly")


class BoardListData(BaseModel):
    """root"""

    post: PostModel = Field(default_factory=PostModel)
    writer: WriterModel = Field(default_factory=WriterModel)
    comment: CommentInfoModel = Field(default_factory=CommentInfoModel)
    count_info: CountInfoModel = Field(default_factory=CountInfoModel, alias="countInfo")
    board_info: BoardInfoModel = Field(default_factory=BoardInfoModel, alias="boardInfo")


class Board_from:
    # Post core
    post_id: UUID | None
    post_user_id: int | None
    post_community_id: int | None
    title: str | None
    body: str | None
    plain_body: str | None
    language_code: str | None
    created_at: str | None
    updated_at: str | None
    is_active: bool | None
    is_baned: bool | None
    status: str | None
    is_updated: bool | None

    # Post media
    photos: list[PhotoDict]
    links: list[LinkDict]
    analyses: list[AnalysisDict]

    # Hashtags
    hashtags: list[Hashtag]

    # Writer
    writer_user_id: int | None
    writer_community_id: int | None
    writer_type: str | None
    writer_community_artist_id: int | None
    writer_is_artist: bool | None
    writer_name: str | None
    writer_image_url: str | None
    writer_bg_image_url: str | None
    writer_is_fanclub_user: bool | None

    # Count info
    comment_count: int | None
    like_count: int | None

    # Comment info
    contentTypeCode: int | None
    readContentId: str | None
    writeContentId: str | None

    # Board info
    board_id: UUID | None
    board_type: str | None
    board_community_id: int | None
    board_name: str | None
    board_is_fanclub_only: bool | None

    def __init__(self, board_list_data: dict[str, Any]) -> None:
        validated_data = BoardListData.model_validate(board_list_data)

        # root
        post = validated_data.post
        writer = validated_data.writer
        comment_info = validated_data.comment
        count_info = validated_data.count_info
        board_info = validated_data.board_info

        # Post core
        self.post_id = post.post_id
        self.post_user_id = post.post_user_id
        self.post_community_id = post.post_community_id
        self.title = post.title
        self.body = post.body
        self.plain_body = post.plain_body
        self.language_code = post.language_code
        self.created_at = post.created_at
        self.updated_at = post.updated_at
        self.is_active = post.is_active
        self.is_baned = post.is_baned
        self.status = post.status
        self.is_updated = post.is_updated

        # Post media 原始資料
        media = post.media
        photos = media.photo
        links = media.link
        analyses = media.analysis

        # Photos normalized
        self.photos: list[PhotoDict] = []
        for p in photos:
            meta = p.image_metadata
            self.photos.append(
                {
                    "media_id": p.media_id,
                    "image_url": p.image_url,
                    "width": meta.width if meta else None,
                    "height": meta.height if meta else None,
                    "published_at": meta.published_at if meta else None,
                }
            )

        # Links normalized
        self.links: list[LinkDict] = links

        # Analyses normalized
        self.analyses: list[AnalysisDict] = []
        for a in analyses:
            self.analyses.append(
                {
                    "media_id": a.media_id,
                    "description": a.description,
                }
            )

        # Hashtags
        self.hashtags: list[Hashtag] = post.hashtags

        # Writer
        self.writer_user_id = writer.writer_user_id
        self.writer_community_id = writer.writer_community_id
        self.writer_type = writer.writer_type
        self.writer_community_artist_id = writer.writer_community_artist_id
        self.writer_is_artist = writer.writer_is_artist
        self.writer_name = writer.writer_name
        self.writer_image_url = writer.writer_image_url
        self.writer_bg_image_url = writer.writer_bg_image_url
        self.writer_is_fanclub_user = writer.writer_is_fanclub_user

        # Count info
        self.comment_count = count_info.comment_count

        # Comment info
        self.contentTypeCode = comment_info.content_type_code
        self.readContentId = comment_info.read_content_id
        self.writeContentId = comment_info.write_content_id
        self.like_count = count_info.like_count

        # Board info
        self.board_id = board_info.board_id
        self.board_type = board_info.board_type
        self.board_community_id = board_info.board_community_id
        self.board_name = board_info.board_name
        self.board_is_fanclub_only = board_info.board_is_fanclub_only
