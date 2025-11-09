from __future__ import annotations

import builtins
import re
import urllib
from urllib.parse import urlparse, ParseResult
from collections import defaultdict
from typing import Any, ClassVar, Literal, NamedTuple, Never
from pydantic import BaseModel, Field
from urllib.parse import urlparse

from berrizdown.lib.__init__ import use_proxy
from berrizdown.static.color import Color
from berrizdown.unit.community.community import custom_dict, get_community
from berrizdown.unit.handle.handle_board_from import BoardMain
from berrizdown.unit.handle.handle_choice import Handle_Choice
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import (
    Arits,
    BerrizAPIClient,
    Public_context,
    is_valid_uuid,
)

logger = setup_logging("interface", "violet")


class MediaLists(NamedTuple):
    vod_list: list[dict[str, Any]]
    photo_list: list[dict[str, Any]]
    live_list: list[dict[str, Any]]
    post_list: list[dict[str, Any]]
    notice_list: list[dict[str, Any]]
    cmt_list: list[dict[str, Any]]


class selected_media_list:
    MediaLists([], [], [], [], [], [])
    post_list: list[dict[str, Any]] = []
    notice_list: list[dict[str, Any]] = []
    cmt_list: list[dict[str, Any]] = []
    vod_list: list[dict[str, Any]] = []
    photo_list: list[dict[str, Any]] = []
    live_list: list[dict[str, Any]] = []


class ArtisComment(BaseModel):
    code: str
    message: str

    class Data(BaseModel):
        hasNext: bool
        totalCount: int

        class Cursor(BaseModel):
            next: int

        class ContentItem(BaseModel):
            class Author(BaseModel):
                appLanguageCode: str
                artistId: str
                authorCountryCode: str
                authorDisplayImage: str
                authorDisplayName: str
                authorId: str
                isFanclubUser: bool
                type: Literal["ARTIST"]

            class Element(BaseModel):
                contentTypeCode: int
                createdAt: str
                parentSeq: int
                replyCount: int
                seq: int
                status: Literal["N"]
                text: str
                updatedAt: str
                writeLanguageCode: str

            class Media(BaseModel):
                photo: Any

            class Reference(BaseModel):
                contentId: str
                contentTypeCode: int

            author: Author
            element: Element
            media: Media
            reference: Reference

        contents: list[ContentItem]
        cursor: Cursor

    data: Data


class UserComment(BaseModel):
    code: str
    message: str

    class Data(BaseModel):
        hasNext: bool
        totalCount: int

        class Cursor(BaseModel):
            next: int

        class ContentItem(BaseModel):
            class Author(BaseModel):
                appLanguageCode: str
                artistId: str | None
                authorCountryCode: str
                authorDisplayImage: str
                authorDisplayName: str
                authorId: str
                isFanclubUser: bool
                type: Literal["USER", "ARTIST", ""]

            class Element(BaseModel):
                contentTypeCode: int
                createdAt: str
                parentSeq: int
                replyCount: int
                seq: int
                status: Literal["N"]
                text: str
                updatedAt: str
                writeLanguageCode: str

            class Media(BaseModel):
                photo: Any

            class Reference(BaseModel):
                contentId: str
                contentTypeCode: int

            author: Author
            element: Element
            media: Media
            reference: Reference

        contents: list[ContentItem]
        cursor: Cursor

    data: Data


class CommentReplies(BaseModel):
    code: str
    message: str

    class Data(BaseModel):
        hasNext: bool
        totalCount: int

        class Cursor(BaseModel):
            next: int

        class ContentItem(BaseModel):
            class Author(BaseModel):
                appLanguageCode: str
                artistId: str | None
                authorCountryCode: str
                authorDisplayImage: str
                authorDisplayName: str
                authorId: str
                isFanclubUser: bool
                type: Literal["USER", "ARTIST", ""]

            class Element(BaseModel):
                contentTypeCode: int
                createdAt: str
                parentSeq: int
                replyCount: int
                seq: int
                status: Literal["N"]
                text: str
                updatedAt: str
                writeLanguageCode: str

            class Media(BaseModel):
                photo: Any

            class Reference(BaseModel):
                contentId: str
                contentTypeCode: int

            class Parent(BaseModel):
                author: CommentReplies.Data.ContentItem.Author
                element: CommentReplies.Data.ContentItem.Element
                media: CommentReplies.Data.ContentItem.Media
                reference: CommentReplies.Data.ContentItem.Reference

            author: Author
            element: Element
            media: Media
            reference: Reference
            parent: Parent | None

        contents: list[ContentItem]  # Allow empty List [] | Full dict
        cursor: Cursor

    data: Data


class Comment(BaseModel):
    code: str
    message: str

    class Data(BaseModel):
        class Content(BaseModel):
            class Author(BaseModel):
                appLanguageCode: str
                artistId: str | None
                authorCountryCode: str
                authorDisplayImage: str
                authorDisplayName: str
                authorId: str
                isFanclubUser: bool
                type: Literal["USER", "ARTIST", ""]

            class Element(BaseModel):
                contentTypeCode: int
                createdAt: str
                parentSeq: int
                replyCount: int
                seq: int
                status: Literal["N"]
                text: str
                updatedAt: str
                writeLanguageCode: str

            class Media(BaseModel):
                photo: Any

            class Reference(BaseModel):
                contentId: str
                contentTypeCode: int

            author: Author
            element: Element
            media: Media
            reference: Reference

        # Allow empty List [] | Full dict
        content: Content | list

    data: Data


class PostDetil(BaseModel):
    code: str
    message: str

    class Data(BaseModel):
        class BoardInfo(BaseModel):
            boardId: str
            boardType: Literal["USER", "ARTIST", ""]
            communityId: int
            isFanclubOnly: bool
            name: str

        class Comment(BaseModel):
            contentTypeCode: int
            readContentId: str
            writeContentId: str

        class Community(BaseModel):
            communityId: int
            communityKey: str
            createdAt: str
            createdBy: str | None
            description: str
            imageUrl: str
            liveImageUrl: str
            mediaCategoryIdSet: list[int]
            name: str
            pcImageUrl: str
            updatedAt: str
            updatedBy: str | None

        class Permission(BaseModel):
            accessible: list[Literal["ADMIN", "USER", "ARTIST", "BUSINESS_PARTNER"]]
            commentWritable: list[Literal["ADMIN", "USER", "ARTIST", "BUSINESS_PARTNER"]]
            writable: list[Literal["ADMIN", "USER", "ARTIST", "BUSINESS_PARTNER"]]

        class Post(BaseModel):
            body: str
            communityId: int
            createdAt: str
            hashtags: Any
            isActive: bool
            isBaned: bool
            isUpdated: bool
            languageCode: str

            class Media(BaseModel):
                analysis: Any
                link: list[str]
                photo: Any

            media: "PostDetil.Data.Post.Media"
            plainBody: str
            postId: str
            status: Literal["ACTIVE", "INACTIVE"] | str
            title: str
            updatedAt: str
            userId: int

        class Writer(BaseModel):
            bgImageUrl: str
            communityArtistId: str | int | None
            communityId: int
            imageUrl: str
            isArtist: bool
            isFanclubUser: bool
            name: str
            type: Literal["USER", "ARTIST", ""]
            userId: int

        boardInfo: "PostDetil.Data.BoardInfo"
        comment: "PostDetil.Data.Comment"
        community: "PostDetil.Data.Community"
        permission: "PostDetil.Data.Permission"
        post: "PostDetil.Data.Post"
        writer: "PostDetil.Data.Writer"

    data: Data


class PostResponse(BaseModel):
    code: str
    message: str

    class BoardInfo(BaseModel):
        boardId: str
        boardType: str
        communityId: int
        isFanclubOnly: bool
        name: str

    class CommentInfo(BaseModel):
        contentTypeCode: int
        readContentId: str
        writeContentId: str

    class CommunityInfo(BaseModel):
        communityId: int
        communityKey: str
        createdAt: str
        createdBy: str | None = None
        description: str | None = ""
        imageUrl: str | None = None
        liveImageUrl: str | None = None
        mediaCategoryIdSet: list[int] = []
        name: str
        pcImageUrl: str | None = None
        updatedAt: str
        updatedBy: str | None = None

    class PermissionInfo(BaseModel):
        accessible: list[str]
        commentWritable: list[str]
        writable: list[str]

    class MediaMetadata(BaseModel):
        height: int
        width: int
        publishedAt: int

    class MediaPhoto(BaseModel):
        imageMetadata: PostResponse.MediaMetadata
        imageUrl: str
        mediaId: str

    class MediaAnalysis(BaseModel):
        description: str
        mediaId: str

    class MediaInfo(BaseModel):
        analysis: list[PostResponse.MediaAnalysis] = []
        link: list[Any] = []
        photo: list[PostResponse.MediaPhoto] = []

    class PostInfo(BaseModel):
        body: str
        communityId: int
        createdAt: str
        hashtags: Any
        isActive: bool
        isBaned: bool
        isUpdated: bool
        languageCode: str
        media: PostResponse.MediaInfo
        plainBody: str
        postId: str
        status: str
        title: str | None = ""
        updatedAt: str
        userId: int

    class WriterInfo(BaseModel):
        bgImageUrl: str | None = ""
        communityArtistId: int|None
        communityId: int
        imageUrl: str | None = None
        isArtist: bool
        isFanclubUser: bool
        name: str
        type: str
        userId: int

    class Data(BaseModel):
        boardInfo: PostResponse.BoardInfo | None = Field(default_factory=dict)
        comment: PostResponse.CommentInfo | None = Field(default_factory=dict)
        community: PostResponse.CommunityInfo | None = Field(default_factory=dict)
        permission: PostResponse.PermissionInfo | None = Field(default_factory=dict)
        post: PostResponse.PostInfo | None = Field(default_factory=dict)
        writer: PostResponse.WriterInfo | None = Field(default_factory=dict)

    data: Data


class Media:
    def __init__(self, info_tuple: tuple[str, object, list[str]]):
        self.info_tuple = info_tuple
        self.community_id = info_tuple[0]
        self.community_name = info_tuple[1]
        self.mediaType = info_tuple[2]
        self.parsed = info_tuple[3]
        self.segments = info_tuple[4]
        self._public_context: Public_context | None = None

    @property
    def public_context(self) -> Public_context:
        if self._public_context is None:
            self._public_context = Public_context()
        return self._public_context

    async def request_publicinfo(self) -> Public_context:
        data: dict = {}
        data: dict[str, Any] = await self.public_context.get_public_context(self.segments[-1], use_proxy)
        if data[0].get("code") == "0000":
            return data
        else:
            logger.error("Fail to get public context")
            return {}

    def media_dict(self, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        d = payloads[0].get("data", {})
        m = d.get("media", {})
        for k in (
            "comment",
            "communityArtists",
            "mediaCategories",
            "videoRatingAssessment",
        ):
            if k in d:
                m[k] = d[k]
        return m

    async def main(self) -> dict[str, Any]:
        if is_valid_uuid(self.segments[-1]) is True:
            data: dict[str, Any] = self.media_dict(await self.request_publicinfo())
            if data != {}:
                return data
            return {}
        else:
            await error_handle("UUID", self.segments[-1], "/".join(self.segments))


class CMT:
    def __init__(self, info_tuple: tuple[str, object, list[str]]):
        self.info_tuple = info_tuple
        self.community_id = info_tuple[0]
        self.community_name = info_tuple[1]
        self.mediaType = info_tuple[2]
        self.parsed = info_tuple[3]
        self.segments = info_tuple[4]
        self._artis: Arits | None = None
        self.data: dict = {}

    @property
    def artis(self) -> Arits:
        if self._artis is None:
            self._artis = Arits()
        return self._artis

    def build_params(self, contentTypeCode: str | int, contentId: str | int):
        return {
            "contentTypeCode": contentTypeCode,
            "contentId": contentId,
            "pageSize": "999999999",
            "languageCode": "en",
        }

    async def _artis_comment(self, params: dict) -> ArtisComment | dict:
        _data: ArtisComment = ArtisComment.model_validate(await self.artis.artis_comment(self.community_id, params, use_proxy))

        if _data.code == "0000":
            return _data.model_dump()["data"]["contents"]

        logger.error(
            f"Fail to get https://svc-api.berriz.in/service/v1/comment/{self.community_id}/artists/comments?contentTypeCode={params['contentTypeCode']}&contentId={params['contentId']}&pageSize=999999999&languageCode=en"
        )
        return {}

    async def _user_comment(self, params: dict) -> dict:
        test = await self.artis.user_comment(params, use_proxy)
        _data: UserComment = UserComment.model_validate(test)

        if _data.code == "0000":
            return _data.model_dump()["data"]["contents"]

        logger.error(f"Fail to get https://svc-api.berriz.in/service/v1/comment/comments/?contentTypeCode={params['contentTypeCode']}&contentId={params['contentId']}&pageSize=999999999&languageCode=en")
        return {}

    async def comment_replies(self, contentTypeCode: str | int, contentId: str | int, parent_seq: str | int, Force_req_user: bool = False) -> list[dict]|dict:
        _data: CommentReplies = CommentReplies.model_validate(await self.artis.comment_replies(self.community_id, contentTypeCode, contentId, parent_seq, use_proxy))

        if _data.code == "0000":
            comment_content: dict | list = _data.model_dump().get("data", {}).get("contents", {})
            if comment_content != []:
                return comment_content

            commend_list: list[dict] = await self._artis_comment(self.build_params(contentTypeCode, contentId))
            board_replies: list[dict] = self.map_artis_command(commend_list, contentTypeCode, contentId, parent_seq)
            if board_replies == [] or Force_req_user is True:
                commend_list: list[dict] = await self._user_comment(self.build_params(contentTypeCode, contentId))
                return self.map_user_command(commend_list, contentTypeCode, contentId, parent_seq)
            else:
                return board_replies

        logger.error(f"Fail to get https://svc-api.berriz.in/service/v1/comment/{self.community_id}/artists/{parent_seq}/replies?contentTypeCode={contentTypeCode}&contentId={contentId}&pageSize=999999999&languageCode=en")
        return {}

    async def request_cmt_info(self, comment_type: str) -> Public_context|dict:
        match comment_type:
            case "reply":
                try:
                    comment_id: str = self.parsed.query.split("=")[1]
                except IndexError:
                    comment_id:str = ""
                if comment_id.isdigit() is True:
                    self.data: Comment = Comment.model_validate(await self.artis.comment(int(comment_id), use_proxy)).model_dump()
                    if self.data.get("code") == "0000":
                        self.data["board_replies"] = await self.comment_replies(
                            self.data["data"]["content"]["reference"]["contentTypeCode"],
                            self.data["data"]["content"]["reference"]["contentId"],
                            self.data["data"]["content"]["element"]["seq"],
                        )
                        return self.data
                await error_handle("replay Code", f"{comment_id} {self.parsed.query}", "/".join(self.segments))
                await BerrizAPIClient().close_session()
                return {}
            case "comment":
                self.data: PostDetil = PostDetil.model_validate(await self.artis.post_detil(self.community_id, self.segments[-1], use_proxy)).model_dump()
                if self.data.get("code") == "0000":
                    params: dict = self.build_params(
                        self.data["data"]["comment"]["contentTypeCode"],
                        self.data["data"]["comment"]["readContentId"],
                    )
                    self.data["board_comment"] = await self._artis_comment(params)
                    if self.data["board_comment"] != []:
                        return self.data
                    self.data["board_comment"] = await self._user_comment(params)
                    if self.data["board_comment"] != []:
                        return self.data
                    return {}
                else:
                    return {}

    def map_artis_command(self, commend_list: list[dict], contentTypeCode: str | int, contentId: str | int, parent_seq: str | int):
        """
        Args:
            commend_list (list): 包含命令字典的列表，每個字典預期包含 'reference' 和 'element' 鍵
            contentTypeCode (str/int): 要比對的內容類型碼
            contentId (str/int): 要比對的內容 ID
            parent_seq (str/int): 要比對的父級元素序列號 (seq)

        Returns:
            list: 包含所有符合篩選條件的原始命令字典的列表
        """
        return list(
            map(
                lambda x: x,
                filter(
                    lambda i: (
                        isinstance(i.get("reference"), dict)
                        and i.get("reference").get("contentId") is not None
                        and i.get("reference").get("contentTypeCode") is not None
                        and str(i.get("reference").get("contentId")) == str(contentId)
                        and str(i.get("reference").get("contentTypeCode")) == str(contentTypeCode)
                        and isinstance(i.get("element"), dict)
                        and i.get("element").get("seq") is not None
                        and str(i.get("element").get("seq")) == str(parent_seq)
                    ),
                    commend_list,
                ),
            )
        )
        
    def map_user_command(
        self,
        commend_list: list[dict],
        contentTypeCode: str | int,
        contentId: str | int,
        seq: int | str,
    ) -> list[dict]:
        """
        Args:
            commend_list (list): 包含留言字典的列表，每個字典預期包含 'reference' 和 'element' 鍵
            contentTypeCode (str/int): 要比對的內容類型碼
            contentId (str/int): 要比對的內容 ID
            seq (int/str): 要比對的 element.seq

        Returns:
            list: 包含所有符合篩選條件的原始留言字典的列表
        """
        type_code = str(contentTypeCode)
        content_id = str(contentId)
        seq_val = str(seq)

        return [
            cmd
            for cmd in commend_list
            if isinstance(cmd.get("reference"), dict)
            and isinstance(cmd.get("element"), dict)
            and str(cmd["reference"].get("contentId")) == content_id
            and str(cmd["reference"].get("contentTypeCode")) == type_code
            and str(cmd["element"].get("seq")) == seq_val
        ]

    async def comment_dict(self, payloads: dict[str, Any], comment_type: str = None) -> dict[str, Any]:
        """TODO: 預請求完再CMT就不在請求 避免二次請求"""
        match comment_type:
            case "reply":
                if (all(key in payloads for key in ("code", "message", "data", "board_replies"))) and (payloads.get("board_replies") != []) is False:
                    await BerrizAPIClient().close_session()
                    logger.error("Wrong data, no board_replies")
                    return {}
                board_replies: dict = payloads.get("board_replies", {})[0]
                data: dict = payloads.get("data", {}).get("content", {})
                data["communityId"] = self.community_id
                data["communityname"] = self.community_name
                data["publishedAt"] = board_replies["element"]["createdAt"]
                data["contentType"] = "CMT"
                data["board"] = {"boardId": self.segments[2]}
                data["mediaId"] = self.segments[-1]
                data["contentId"] = board_replies["element"]["seq"]
                data["title"] = board_replies["element"]["text"]
                data["userNickname"] = data["author"]["authorDisplayName"]
                data["replyInfo"] = {
                    "isReply": True,
                    "parentCommentSeq": int(self.parsed.query.split("=")[1]),
                }
                return data
            case "comment":
                if payloads == {}:
                    await BerrizAPIClient().close_session()
                    return {}
                data: dict = payloads.get("data", {})
                board_comment: dict = payloads.get("board_comment", {})[0]
                data["communityId"] = self.community_id
                data["communityname"] = self.community_name
                data["publishedAt"] = board_comment["element"]["createdAt"]
                data["contentType"] = "CMT"
                data["board"] = data["boardInfo"]
                data["mediaId"] = self.segments[-1]
                data["contentId"] = board_comment["element"]["seq"]
                data["title"] = board_comment["element"]["text"]
                data["userNickname"] = board_comment["author"]["authorDisplayName"]
                data["replyInfo"] = {
                    "authorName": None,
                    "isReply": False,
                    "parentCommentSeq": -1,
                }
                return data

    async def main(self, comment_type: str = None) -> dict[str, Any]:
        if all([is_valid_uuid(self.segments[2]), is_valid_uuid(self.segments[-1])]):
            data: dict[str, Any] = await self.comment_dict(await self.request_cmt_info(comment_type), comment_type)
            if data != {}:
                return data
            return {}
        else:
            await error_handle(
                "UUID",
                f"{self.segments[-1]} {self.segments[1]}",
                "/".join(self.segments),
            )


class POST:
    def __init__(self, info_tuple: tuple[str, object, list[str]]):
        self.info_tuple = info_tuple
        self.community_id = info_tuple[0]
        self.community_name = info_tuple[1]
        self.mediaType = info_tuple[2]
        self.parsed = info_tuple[3]
        self.segments = info_tuple[4]
        self._artis: Arits | None = None
        self.data: dict = {}

    @property
    def artis(self) -> Arits:
        if self._artis is None:
            self._artis = Arits()
        return self._artis

    def build_params(self, contentTypeCode: str | int, contentId: str | int):
        return {
            "contentTypeCode": contentTypeCode,
            "contentId": contentId,
            "pageSize": "999999999",
            "languageCode": "en",
        }

    async def request_post_info(self):
        data: PostResponse = PostResponse.model_validate(await self.artis.post_detil(self.community_id, self.segments[-1], use_proxy)).model_dump()
        if data.get("code") == "0000":
            return data.get("data", {})
        else:
            return {}

    async def boardmain(self, data: dict[str, Any]) -> dict[str, Any] | Never:
        if data == {}:
            await BerrizAPIClient().close_session()
            assert Never
        return (await BoardMain(data).main())[0]

    async def main(self) -> dict[str, Any]:
        if all([is_valid_uuid(self.segments[2]), is_valid_uuid(self.segments[-1])]):
            data: dict[str, Any] = await self.boardmain(await self.request_post_info())
            if data != {}:
                return data
            return {}
        else:
            await error_handle(
                "UUID",
                f"{self.segments[-1]} {self.segments[1]}",
                "/".join(self.segments),
            )


class URL_Parser:
    def __init__(self, urls: list[str]|str):
        self.urls: list[str]|str = urls

    async def normalization(self, parsed: urllib) -> list[str]:
        segments: list[str] = parsed.path.strip("/").split("/")
        community_id: int | None = await self.community_name_check(segments[0])
        if community_id is None:
            await error_handle("community_name", segments[0], "/".join(segments))
        else:
            community_name = segments[0]
            process_type: str = self.classification(parsed, segments)
            info_tuple: tuple[str, str, str, object, list[str]] = self.make_info_tuple(community_id, community_name, process_type, parsed, segments)
            if await self.make_selected_media_list(info_tuple) is True:
                return True
            else:
                await error_handle("Type", f"{segments[1]}{segments[3]}", "/".join(segments))
                return False

    def classification(self, parsed: object, segments: list[str]) -> str:
        if "media" in segments and "content" in segments:
            if is_valid_uuid(segments[-1]) is True:
                return "media"
        if "live" in segments or "replay" in segments:
            if is_valid_uuid(segments[-1]) is True:
                return "live"
        if "notice" in segments:
            return "notice"
        if "board" in segments and "post" in segments and "reply" in parsed.query:
            return "reply"
        if "board" in segments and "post" in segments and "comment" in parsed.query:
            return "comment"
        if "board" in segments and "post" in segments:
            return "post"
        elif "board" in segments:
            return "board"
        return "unknown"

    def make_info_tuple(
        self,
        community_id: str,
        community_name: str,
        media_type: str,
        parsed: urllib,
        segments: list[str],
    ) -> tuple[str, object, list[str]]:
        return (community_id, community_name, media_type, parsed, segments)

    async def make_selected_media_list(self, info_tuple: tuple[str, str, str, object, list[str]]) -> bool:
        match info_tuple[2]:
            case "media":
                public_context: dict = await Media(info_tuple).main()
                if public_context == {}:
                    return False
                match public_context.get("mediaType").replace("'", ""):
                    case "VOD":
                        selected_media_list.vod_list.append(public_context)
                        return True
                    case "PHOTO":
                        selected_media_list.photo_list.append(public_context)
                        return True
                    case "YOUTUBE":
                        await error_handle(
                            "Media",
                            "Not supported youtube content",
                            "YT-DLP is best Solution.",
                        )
                        return True
            case "live":
                public_context: dict = await Media(info_tuple).main()
                if public_context == {}:
                    return False
                selected_media_list.live_list.append(public_context)
                return True
            case "notice":
                notice_dict: dict = {
                    "communityId": info_tuple[0],
                    "isFanclubOnly": False,
                    "mediaId": info_tuple[4][-1],
                    "mediaType": "NOTICE",
                }
                selected_media_list.notice_list.append(notice_dict)
                return True
            case "reply":
                comment_context: dict = await CMT(info_tuple).main("reply")
                if comment_context:
                    selected_media_list.cmt_list.append(comment_context)
                    return True
            case "comment":
                comment_context: dict = await CMT(info_tuple).main("comment")
                if comment_context:
                    selected_media_list.cmt_list.append(comment_context)
                    return True
            case "post":
                comment_context: dict = await POST(info_tuple).main()
                if comment_context:
                    selected_media_list.post_list.append(comment_context)
                    return True
            case "board":
                await error_handle("POST ID", "Not found post id", "/".join(info_tuple[4]))
                return True
            case "unknown":
                return False

    def urlparse(self, url: str) -> str:
        return url.replace("/web/main", "").replace("/applink", "").replace("app/main", "")

    async def community_name_check(self, community_name: str) -> int:
        return await get_community(community_name)

    def url2berrizin(self, url: str) -> ParseResult:
        url = re.sub(
            r"(berriz\.in/applink(/web)?|link\.berriz\.in/(app|web)?/main)",
            "berriz.in",
            url
        )
        url = re.sub(r'(?<!:)//+', '/', url)
        url = re.sub(r"/(web|main)(?=/|$)", "", url)
        parsed = urlparse(url)
        # 強製網域為 berriz.in
        parsed = parsed._replace(netloc="berriz.in")
        return parsed

    async def parser(self) -> bool:
        urls = self.urls
        if isinstance(urls, str):
            urls = (urls,)
        elif urls is None:
            urls = ()

        all_results = []
        for url in urls:
            result = None
            if isinstance(url, str):
                url = url.replace("/ko", "").replace("/en", "")
                parsed = self.url2berrizin(self.urlparse(url))
                
                if parsed.netloc == "berriz.in":
                    try:
                        result = await self.normalization(parsed)
                        all_results.append(result)
                    except Exception as e:
                        logger.error(f"Error during normalization of {url}: {e}")
                        pass 
                else:
                    await error_handle("domain", parsed.netloc, url)
                    
            elif not isinstance(url, str):
                await error_handle("Type", url, "Unknown Type")
        
        if not all_results:
            return False
        return all(result is True for result in all_results)


class Community_Uniqueness:
    SOURCE_TYPES: ClassVar[list[str]] = ["vods", "lives", "photos", "post", "notice", "cmt"]

    @classmethod
    async def group_by_community(cls) -> list[dict]:
        """
        將來自不同媒體來源的項目按 `communityId` 進行分組

        這個方法會迭代所有定義的媒體列表 (`selected_media_list` 的屬性)，
        並將每個含有 `communityId` 的項目歸類到對應的社羣組中
        最後，它會非同步地解析每個社羣 ID 對應的名稱，並以特定的格式返回分組結果

        參數:
            cls: 類別本身 (Class Method 的慣例參數)

        返回:
            一個列表，其中每個元素是一個字典該字典的鍵是一個 tuple
            (community_id, community_name, custom_community_name)，
            而值是另一個字典，包含按 SOURCE_TYPES 分組的媒體列表
            例如：`[{(cid, cm_name, custom_cm_name): {'vods': [...], 'photos': [...], ...}}]`
        """
        sources = {
            "vods": selected_media_list.vod_list,
            "lives": selected_media_list.live_list,
            "photos": selected_media_list.photo_list,
            "post": selected_media_list.post_list,
            "notice": selected_media_list.notice_list,
            "cmt": selected_media_list.cmt_list,
        }
        # 以 communityId 分組 並為每個Community ID {key} 用sources中5個List當作{value}
        # 初始化 community_groups: 鍵為 communityId (cid)，值為一個字典，
        # 該字典的鍵為 SOURCE_TYPES，值為一個空列表，用於累積該社羣下的媒體項目
        community_groups = defaultdict(lambda: {k: [] for k in cls.SOURCE_TYPES})

        for source_name, items in sources.items():
            for item in items:
                match item:
                    case None:
                        pass
                    case _:
                        cid = item.get("communityId")
                        if cid is not None:
                            community_groups[cid][source_name].append(item)
                        else:
                            logger.warning(f"Input has no communityId fail to make selected_media_list {Color.fg('light_gray')}{item}{Color.reset()}")
                            logger.error("Fail parse or get communityId from input data")
        """{(cid, cm_name, custom_cm_name):{'vods': [], 'photos': [], 'post': [], 'notice': [], 'cmt': []}}}}"""
        result = []

        for cid, srcs in community_groups.items():
            cm_name: str = await get_community(cid)
            custom_cm_name: str = await custom_dict(cm_name)
            result.append({(cid, cm_name, custom_cm_name): srcs})
        """return is single List[Dict]"""
        return result


class StartProcess:
    """
    負責啟動處理選定的媒體列表的程式

    該類別會迭代 `selected_media_list` 中的每個字典每個字典的鍵預期
    是一個包含 (社羣ID, 社羣名稱, 自訂社羣名稱) 的 tuple，而其值則是一個
    代表選定媒體項目的列表
    """

    def __init__(self, selected_media_list: list[dict[str, Any]]) -> None:
        """
        初始化 StartProcess 實例

        參數:
            selected_media_list: 一個列表，其中包含表示選定媒體資料的字典
                                 每個字典的鍵是一個 tuple (community_id, community_name, custom_community_name)，
                                 其值是一個包含媒體資料的列表
        """
        self.selected_media_list = selected_media_list
        
    async def process(self) -> list[builtins.dict]:
        """
        迭代選定的媒體列表，並為每個社羣/媒體組合啟動處理程式

        對於列表中的每個字典：
        1. 迭代其鍵/值對
        2. 檢查鍵是否為 tuple (預期包含社羣資訊)
        3. 如果鍵是 tuple，則解構其內容 (community_id, community_name, custom_community_name)
        4. 使用這些資訊初始化 Handle_Choice (HC) 實例
        5. 將選定的媒體資料 (字典的值) 傳遞給 HC 實例進行處理
        6. 呼叫 HC 實例的異步方法來處理選定的媒體，並等待結果
        """
        for dict in self.selected_media_list:
            for key, value in dict.items():
                if isinstance(key, tuple):
                    community_id, community_name, custom_community_name = key

                    HC = Handle_Choice(community_id, community_name, custom_community_name)
                    await HC.user_selected_media(value)
                    await HC.process_selected_media()


async def error_handle(invalid_name: str, error_object: str, url: str) -> None:
    logger.warning(f"Invalid {invalid_name}: {Color.bg('cyan')}{error_object}{Color.reset()}{Color.fg('gold')} remove process {Color.fg('light_gray')}{url}{Color.reset()}")
    await BerrizAPIClient().close_session()