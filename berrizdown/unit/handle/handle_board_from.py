import asyncio
from collections.abc import Iterable
from datetime import datetime
from functools import cached_property
from typing import Any

from lib.__init__ import OutputFormatter, use_proxy
from lib.load_yaml_config import CFG
from lib.name_metadata import fmt_dir, meta_name
from static.Board_from import Board_from
from static.Notice import Notice, Notice_info
from static.parameter import paramstore
from unit.__init__ import FilenameSanitizer
from unit.community.community import custom_dict, get_community
from unit.date.date import get_formatted_publish_date
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Arits, Translate

logger = setup_logging("handle_board_from", "midnight_blue")


class BoardFetcher:
    def __init__(self, index: dict[str, Any]):
        self.json_data: dict[str, Any] | None = None
        self.fetcher: Any = Board_from(index)

    def get_postid(self) -> Any:
        return self.fetcher.post_id

    def get_community_id(self) -> Any:
        return self.fetcher.post_community_id

    def get_title(self) -> str:
        return self.fetcher.title

    def get_plainbody(self) -> str:
        return self.fetcher.plain_body

    def get_createdAt(self) -> str:
        return self.fetcher.created_at

    def get_updatedAt(self) -> str:
        return self.fetcher.updated_at

    def get_links(self) -> Any:
        return self.fetcher.links

    def get_photos(
        self,
    ) -> tuple[
        list[str | None],
        list[str | None],
        list[tuple[int | None, int | None]],
        list[str | None],
    ]:
        media_ids: list[str | None] = []
        image_urls: list[str | None] = []
        dimensions: list[tuple[int | None, int | None]] = []
        published_dates: list[str | None] = []
        for p in self.fetcher.photos:
            if not isinstance(p, dict):
                continue
            media_ids.append(p.get("media_id"))
            image_urls.append(p.get("image_url"))
            dimensions.append((p.get("width"), p.get("height")))
            published_dates.append(p.get("published_at"))

        return media_ids, image_urls, dimensions, published_dates

    def get_analysis(self) -> Any:
        return self.fetcher.analyses

    def get_hashtags(self) -> Any:
        return self.fetcher.hashtags

    def get_contentTypeCode(self) -> int:
        return self.fetcher.contentTypeCode

    def get_readContentId(self) -> int:
        return self.fetcher.readContentId

    def get_writeContentId(self) -> int:
        return self.fetcher.writeContentId

    def get_writer_user_id(self) -> Any:
        return self.fetcher.writer_user_id

    def get_writer_community_id(self) -> Any:
        return self.fetcher.writer_community_id

    def get_writer_type(self) -> Any:
        return self.fetcher.writer_type

    def get_writer_name(self) -> str:
        return self.fetcher.writer_name

    def get_board_id(self) -> Any:
        return self.fetcher.board_id

    def get_board_name(self) -> str:
        return self.fetcher.board_name

    def get_board_is_fanclub_only(self) -> bool:
        return self.fetcher.board_is_fanclub_only

    def get_board_community_id(self) -> Any:
        return self.fetcher.board_community_id


class NoticeFetcher:
    def __init__(self, index: dict[str, Any]):
        self.json_data: dict[str, Any] | None = None
        self.fetcher: Any = Notice(index)

    def get_code(self) -> str:
        return self.fetcher.code

    def get_message(self) -> str:
        return self.fetcher.message

    def get_cursor_next(self) -> Any:
        return self.fetcher.cursor_next

    def get_has_next(self) -> bool:
        return self.fetcher.has_next

    def get_notices(self) -> Any:
        return self.fetcher.notices


class NoticeINFOFetcher:
    def __init__(self, index: dict[str, Any]):
        self.fetcher_info: Any = Notice_info(index)

    def get_communityNoticeId(self) -> int:
        return self.fetcher_info.communityNoticeId

    def get_title(self) -> str:
        return self.fetcher_info.title

    def get_body(self) -> str:
        return self.fetcher_info.body

    def get_eventId(self) -> int | None:
        return self.fetcher_info.eventId

    def get_reservedAt(self) -> str:
        return self.fetcher_info.reservedAt


class BoardMain:
    def __init__(
        self,
        board_list: list[dict[str, Any]] | dict[str, Any],
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ):
        self.board_list: list[dict[str, Any]] | dict[str, Any] = board_list
        self.boardfetcher: Any = BoardFetcher
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b
        self.FilenameSanitizer = FilenameSanitizer

    async def main(self) -> list[dict[str, Any]]:
        task: list[list[dict[str, Any]]] = []
        for index in self.sort_by_time():
            fetcher: BoardFetcher = self.boardfetcher(index)
            contentTypeCode: int = fetcher.get_contentTypeCode()
            contentId: int = fetcher.get_readContentId()
            postid: Any = fetcher.get_postid()
            image_info: tuple[
                list[str | None],
                list[str | None],
                list[tuple[int | None, int | None]],
                list[str | None],
            ] = fetcher.get_photos()
            community_id: Any = fetcher.get_board_community_id() or 2 * 23 - 1
            writer_name: str = fetcher.get_writer_name()
            board_name: str = fetcher.get_board_name()
            fanclub_only: bool = fetcher.get_board_is_fanclub_only()
            ISO8601: str = fetcher.get_createdAt()
            title: str = fetcher.get_plainbody()[:64].replace("\n", " ").replace("\r", " ").strip()
            save_title = self.FilenameSanitizer.sanitize_filename(title)

            mediaid: list[str | None] = image_info[0]
            folder_name, formact_time_str, video_meta = self.get_folder_name(fetcher, save_title, ISO8601, board_name, writer_name)
            community_name: str = await self.get_commnity_name(community_id)
            return_data: list[dict[str, Any]] = [
                {
                    "publishedAt": ISO8601,
                    "title": save_title,
                    "mediaType": "POST",
                    "communityId": community_id,
                    "isFanclubOnly": fanclub_only,
                    "communityName": community_name,
                    "folderName": folder_name,
                    "timeStr": formact_time_str,
                    "postId": postid,
                    "imageInfo": image_info,
                    "mediaId": mediaid,
                    "board_name": board_name,
                    "writer_name": writer_name,
                    "index": index,
                    "fetcher": fetcher,
                    "video_meta": video_meta,
                    "contentTypeCode": contentTypeCode,
                    "contentId": contentId,
                }
            ]
            task.append(return_data)
        return_data: list[dict[str, Any]] = [item for sublist in task for item in sublist]
        if paramstore.get("fanclub") is True:
            return_data = [d for d in return_data if d.get("isFanclubOnly") is True]
        return return_data

    def sort_by_time(self) -> list[dict[str, Any]]:
        sort_list: list[dict[str, Any]] = []
        # 支援單一 dict 或 list/iterable of dict
        items: Iterable[dict[str, Any]]
        if isinstance(self.board_list, dict):
            items = (self.board_list,)
        else:
            items = self.board_list

        for index in items:
            if not isinstance(index, dict):
                continue

            fetcher: BoardFetcher = self.boardfetcher(index)
            ISO8601: str = fetcher.get_createdAt()

            if ISO8601 and isinstance(self.time_a, datetime) and isinstance(self.time_b, datetime):
                try:
                    published_at: datetime = datetime.fromisoformat(ISO8601.replace("Z", "+00:00"))
                    if not (self.time_a <= published_at <= self.time_b):
                        continue
                except (ValueError, TypeError):
                    continue

            sort_list.append(index)
        return sort_list

    def get_folder_name(
        self,
        fetcher: BoardFetcher,
        title: str,
        ISO8601: str,
        board_name: str,
        writer_name: str,
    ) -> tuple[str, str, dict[str, str]]:
        formact_ISO8601: str = get_formatted_publish_date(ISO8601, fmt_dir)
        dt: datetime = datetime.strptime(formact_ISO8601, fmt_dir)
        d: str = dt.strftime(fmt_dir)
        post_meta: dict[str, str] = meta_name(
            d,
            title,
            board_name,
            writer_name,
        )
        folder_name: str = OutputFormatter(f"{CFG['donwload_dir_name']['dir_name']}").format(post_meta)
        return folder_name, d, post_meta

    async def get_commnity_name(self, community_id: int) -> str:
        group_name: str | int | None = await get_community(community_id)
        if isinstance(group_name, int) or group_name is None:
            raise ValueError(f"Community id {community_id} not found community name")
        return group_name


class BoardNotice(BoardMain):
    def __init__(
        self,
        notice_list: list[dict[str, Any]],
        Community_id: int,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ):
        super().__init__(notice_list, time_a, time_b)
        self.notice: list[dict[str, Any]] = notice_list
        self.noticefetcher: Any = NoticeFetcher
        self.community_id: int = Community_id
        self.FilenameSanitizer = FilenameSanitizer

    def sort_by_time(self) -> list[dict[str, Any]]:
        sort_list: list[dict[str, Any]] = []
        for index in self.notice:
            ISO8601 = index.get("reservedAt")
            if ISO8601 and isinstance(self.time_a, datetime) and isinstance(self.time_b, datetime):
                try:
                    published_at: datetime = datetime.fromisoformat(ISO8601.replace("Z", "+00:00"))
                    if not (self.time_a <= published_at <= self.time_b):
                        continue
                except (ValueError, TypeError):
                    continue
            sort_list.append(index)
        return sort_list

    async def notice_list(self) -> list[dict[str, Any]]:
        notices: list[dict[str, Any]] = self.sort_by_time()
        return_data: list[dict[str, Any]] = [
            {
                "publishedAt": n["reservedAt"],
                "title": self.FilenameSanitizer.sanitize_filename(n["title"]),
                "mediaType": "NOTICE",
                "communityId": self.community_id,
                "isFanclubOnly": False,
                "mediaId": n["communityNoticeId"],
                "index": idx,
            }
            for idx, n in enumerate(notices)
        ]
        return return_data


class BoardNoticeINFO(BoardMain):
    def __init__(
        self,
        notice_list: dict[str, Any],
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ):
        super().__init__(notice_list, time_a, time_b)
        self.notice: dict[str, Any] = notice_list
        self.noticefetcher: Any = NoticeFetcher
        self.noticeinfofetcher: Any = NoticeINFOFetcher
        self.FilenameSanitizer = FilenameSanitizer
        self._AritsClass = Arits

    @cached_property
    def Artis(self) -> Arits:
        return self._AritsClass()

    async def call_notice_page(self, communityNoticeId: int, communityId: int) -> dict[str, Any] | None:
        data = await self.Artis.request_notice_page(communityId, communityNoticeId, use_proxy)
        if data and data.get("code", "") == "0000":
            return data
        return None

    async def request_notice_info(self, communityNoticeId: int, communityId: int) -> Any:
        notice_data = await self.call_notice_page(communityNoticeId, communityId)
        if notice_data is None:
            return None
        return await self.noticemain(communityId, notice_data)

    def noticeget_folder_name(
        self,
        title: str,
        ISO8601: str,
        custom_community_name: str,
    ) -> tuple[str, str, dict[str | int, str]]:
        formact_ISO8601: str = get_formatted_publish_date(ISO8601, fmt_dir)
        dt: datetime = datetime.strptime(formact_ISO8601, fmt_dir)
        d: str = dt.strftime(fmt_dir)
        notice_meta: dict = meta_name(d, title, custom_community_name, "NOTICE")
        folder_name: str = OutputFormatter(f"{CFG['donwload_dir_name']['dir_name']}").format(notice_meta)
        return folder_name, d, notice_meta

    async def _get_custom_community_name(self, community_name: str) -> str:
        temp_custom_name: str | None = await custom_dict(community_name)
        return temp_custom_name if temp_custom_name is not None else community_name

    async def _resolve_community_id(self, community_name: str) -> int:
        temp_raw_id: str | int | None = await get_community(community_name)

        if temp_raw_id is None:
            raise ValueError("Community id is null")

        if isinstance(temp_raw_id, int):
            return temp_raw_id

        if isinstance(temp_raw_id, str):
            try:
                return int(temp_raw_id)
            except ValueError as e:
                raise ValueError(f"Community id invaild faile to convert to int: '{temp_raw_id}'") from e

        raise TypeError(f"get_community got unexpected return type: {type(temp_raw_id)}")

    async def noticemain(self, cid: int, data: dict[str, Any]) -> dict[str, Any]:
        fetcher: NoticeINFOFetcher = self.noticeinfofetcher(data)
        title: str = fetcher.get_title()
        ISO8601: str = fetcher.get_reservedAt()
        safe_title: str = self.FilenameSanitizer.sanitize_filename(title)
        community_name: str = await self.get_commnity_name(cid)

        custom_community_name: str = await self._get_custom_community_name(community_name)
        community_id: int = await self._resolve_community_id(community_name)

        folder_name, formact_time_str, video_meta = self.noticeget_folder_name(safe_title, ISO8601, custom_community_name)

        return {
            "safe_title": safe_title,
            "folderName": folder_name,
            "formact_time_str": formact_time_str,
            "community_name": community_name,
            "custom_community_name": custom_community_name,
            "communityId": community_id,
            "fetcher": fetcher,
            "notice_list": self.notice,
            "notice_meta_info": video_meta,
            "raw": data,
        }


class JsonBuilder:
    def __init__(self, index: dict[str, Any], postid: int, use_proxy: bool = False):
        self.index: dict[str, Any] = index
        self.postid: int = postid
        self.use_proxy: bool = use_proxy

    @cached_property
    def translate(self) -> "Translate":
        return Translate()

    async def build_translated_json(self) -> dict[str, Any | None]:
        translations: dict[str, str | None] = await self.fetch_translations()
        eng: str | None = translations.get("en")
        jp: str | None = translations.get("jp")
        zhHant: str | None = translations.get("zh-Hant")
        zhHans: str | None = translations.get("zh-Hans")

        return self.get_json_formact(eng, jp, zhHant, zhHans)

    def get_json_formact(self, eng: str | None, jp: str | None, zhHant: str | None, zhHans: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index": self.index,
            "translations": {
                "en": eng,
                "jp": jp,
                "zh-Hant": zhHant,
                "zh-Hans": zhHans,
            },
        }
        return payload

    async def fetch_translations(self) -> dict[str, str | None]:
        tasks = [
            self.translate.translate_post(self.postid, "en", self.use_proxy),
            self.translate.translate_post(self.postid, "ja", self.use_proxy),
            self.translate.translate_post(self.postid, "zh-Hant", self.use_proxy),
            self.translate.translate_post(self.postid, "zh-Hans", self.use_proxy),
        ]

        try:
            results: list[str | None] = await asyncio.gather(*tasks)
        except Exception as e:
            raise e
        return {
            "en": results[0],
            "jp": results[1],
            "zh-Hant": results[2],
            "zh-Hans": results[3],
        }
