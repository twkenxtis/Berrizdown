from typing import Any

import orjson


class IMG_PublicContext:
    def __init__(self, public_contexts: list[dict[str, Any]]) -> None:
        if not public_contexts:
            raise ValueError("public_contexts is empty")

        ctx: dict[str, Any] = public_contexts[0]

        # root
        self.code: Any | None = ctx.get("code")
        self.message: Any | None = ctx.get("message")
        data: dict[str, Any] = ctx.get("data", {})

        # data
        media: dict[str, Any] = data.get("media", {})
        community_artists: list[dict[str, Any]] = data.get("communityArtists", [])
        self.community_artists: list[dict[str, Any]] = data.get("communityArtists", [])
        media_categories: list[dict[str, Any]] = data.get("mediaCategories", [])
        comment: dict[str, Any] = data.get("comment", {})

        # media
        self.media_seq: Any | None = media.get("mediaSeq")
        self.media_id: Any | None = media.get("mediaId")
        self.media_type: Any | None = media.get("mediaType")
        self.title: Any | None = media.get("title")
        self.body: Any | None = media.get("body")
        self.thumbnail_url: Any | None = media.get("thumbnailUrl")
        self.published_at: Any | None = media.get("publishedAt")
        self.community_id: Any | None = media.get("communityId")
        self.is_fanclub_only: Any | None = media.get("isFanclubOnly")

        # communityArtists
        self.community_artists_id: Any | None = community_artists[0].get("communityArtistId") if community_artists else ""
        self.community_name: Any | None = community_artists[0].get("name") if community_artists else None
        self.community_artist_image_url: Any | None = community_artists[0].get("imageUrl") if community_artists else "https://berriz.in/apple-icon.png?ae6dbf9a85e7da92"

        # mediaCategories
        self.category_id: Any | None = media_categories[0].get("mediaCategoryId") if media_categories else ""
        self.category_name: Any | None = media_categories[0].get("mediaCategoryName") if media_categories else ""

        # comment
        self.content_type_code: Any | None = comment.get("contentTypeCode")
        self.read_content_id: Any | None = comment.get("readContentId")
        self.write_content_id: Any | None = comment.get("writeContentId")

    def to_dict(self):
        """Convert all data to dictionary"""
        if self.code != "0000":
            return {"error": "Invalid status code"}

        return {
            # Root level
            "code": self.code,
            "message": self.message,
            # Media fields
            "media_seq": self.media_seq,
            "media_id": self.media_id,
            "media_type": self.media_type,
            "title": self.title,
            "body": self.body,
            "thumbnail_url": self.thumbnail_url,
            "published_at": self.published_at,
            "community_id": self.community_id,
            "is_fanclub_only": self.is_fanclub_only,
            # Community artists fields
            "community_artists_id": self.community_artists_id,
            "community_name": self.community_name,
            "community_artist_image_url": self.community_artist_image_url,
            # Media categories fields
            "category_id": self.category_id,
            "category_name": self.category_name,
            # Comment fields
            "content_type_code": self.content_type_code,
            "read_content_id": self.read_content_id,
            "write_content_id": self.write_content_id,
        }

    def to_json(self):
        """Convert to JSON string with pretty formatting"""
        return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2).decode("utf-8")
