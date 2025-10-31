import asyncio
import difflib
from datetime import datetime
from functools import cached_property
from typing import Any, TypedDict

from lib.__init__ import use_proxy
from lib.lock_cookie import cookie_session
from mystate.fanclub import FanClub
from static.color import Color
from static.parameter import paramstore
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Live, MediaList

MediaItem = dict[str, str | dict | bool]
SelectedMedia = dict[str, list[dict]]
MediaResult = tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]
LiveResult = tuple[list[dict[str, Any]], dict[str, Any], bool]

logger = setup_logging("GetMediaList", "turquoise")


class FanClubFilter:
    def __init__(self):
        self.FanClub = FanClub()

    async def is_fanclub(self) -> Any | None:
        context: Any | None = await self.FanClub.fanclub_main()
        """None - not fanclub"""
        match context:
            case "NOFANCLUBINFO":
                return "NOFANCLUBINFO"
            case _:
                return context


class VODDetail(TypedDict):
    duration: int
    videoRating: str | None


class VODMediaItem(TypedDict):
    mediaSeq: int
    mediaId: str
    mediaType: str  # "VOD"
    title: str
    thumbnailUrl: str
    publishedAt: str
    communityId: int
    isFanclubOnly: bool
    youtube: str | None
    photo: str | None
    vod: VODDetail
    communityArtists: list[Any]


class LiveReplayInfo(TypedDict):
    duration: int
    videoRatingAssessmentId: int | None
    videoRating: str | None


class LiveDetail(TypedDict):
    liveStatus: str
    replay: LiveReplayInfo


class CommunityArtist(TypedDict):
    communityArtistId: int
    name: str
    imageUrl: str


class LiveMediaItem(TypedDict):
    mediaSeq: int
    mediaId: str
    mediaType: str  # "LIVE"
    title: str
    thumbnailUrl: str
    publishedAt: str
    communityId: int
    isFanclubOnly: bool
    live: LiveDetail
    communityArtists: list[CommunityArtist]


class PhotoDetail(TypedDict):
    imageCount: int


class PhotoMediaItem(TypedDict):
    mediaSeq: int
    mediaId: str
    mediaType: str  # "PHOTO"
    title: str
    thumbnailUrl: str
    publishedAt: str
    communityId: int
    isFanclubOnly: bool
    youtube: str | None
    photo: PhotoDetail
    vod: Any | None
    communityArtists: list[Any]


class MediaParser:
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_name: str,
        time_a: datetime | None,
        time_b: datetime | None,
    ):
        self.community_id = community_id
        self.communityname = communityname
        self.custom_communityname = custom_name or communityname
        self.time_a = time_a
        self.time_b = time_b
        self._fanclub_filter: FanClubFilter | None = None

    @property
    def FanClubFilter(self) -> "FanClubFilter":
        if self._fanclub_filter is None:
            self._fanclub_filter = FanClubFilter()
        return self._fanclub_filter

    async def parse(
        self, _data: dict[str, Any]
    ) -> tuple[
        list["VODMediaItem"],
        list["PhotoMediaItem"],
        list["LiveMediaItem"],
        str | None,
        bool,
    ]:
        # Chunk 1: extract core
        FCINFO: str | None = await self.FanClubFilter.is_fanclub()
        contents, cursor, has_next = await self._extract_core(_data)
        if contents is None:
            return [], [], [], cursor, has_next

        # Chunk 2: parse three raw lists
        raw_vods: list[VODMediaItem]
        raw_photos: list[PhotoMediaItem]
        raw_lives: list[LiveMediaItem]
        raw_vods, raw_photos, raw_lives = self._extract_media_items(contents)

        # Chunk 3: split fanclub vs non-fanclub
        v_fc, v_nfc = self.fanclub_items(raw_vods)
        p_fc, p_nfc = self.fanclub_items(raw_photos)
        l_fc, l_nfc = self.fanclub_items(raw_lives)

        output_vods, output_photos, output_lives = v_nfc, p_nfc, l_nfc

        has_valid_cookie: bool = not (cookie_session == {} or paramstore.get("no_cookie") is True)

        if has_valid_cookie:
            is_fanclub_match: bool = True
            if FCINFO is not None:
                ratio1 = difflib.SequenceMatcher(None, FCINFO.lower(), self.communityname.lower()).ratio()
                ratio2 = difflib.SequenceMatcher(None, FCINFO.lower(), self.custom_communityname.lower()).ratio()
                if ratio1 < 0.8 and ratio2 < 0.8:
                    is_fanclub_match = False
            pref: bool | None = paramstore.get("fanclub")
            if pref is True:
                output_vods, output_photos, output_lives = v_fc, p_fc, l_fc
            elif pref is False or not is_fanclub_match:
                pass
            else:
                output_vods = v_fc + v_nfc
                output_photos = p_fc + p_nfc
                output_lives = l_fc + l_nfc
        return output_vods, output_photos, output_lives, cursor, has_next

    async def _extract_core(self, _data: dict[str, Any]) -> tuple[list[dict] | None, str | None, bool]:
        if not self._is_valid_response(_data):
            return None, None, False
        contents, (cursor, has_next) = await asyncio.gather(self._get_contents(_data), self._extract_pagination(_data))
        return contents, cursor, has_next

    async def parse_fanclub_community(self, contents: list[dict]) -> list[dict]:
        return [item for item in contents if item.get("media", {}).get("communityId") == self.community_id and item["media"].get("isFanclubOnly") is True]

    def _is_valid_response(self, _data: dict[str, Any]) -> bool:
        if _data is None:
            return False
        code: str | None = _data.get("code")
        if code != "0000":
            logger.warning(f"API error: {code}")
            return False
        return True

    async def _get_contents(self, _data: dict[str, Any]) -> list[dict]:
        return _data.get("data", {}).get("contents", [])

    def _is_within_time_range(self, published_at_str: str | None) -> bool:
        if not (isinstance(self.time_a, datetime) and isinstance(self.time_b, datetime)):
            return True
        if not published_at_str:
            return False
        try:
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            return self.time_a <= published_at <= self.time_b
        except (ValueError, TypeError):
            return False

    def _classify_media(self, media: dict[str, Any]) -> str | None:
        return media.get("mediaType")

    def _extract_media_items(self, contents: list[dict[str, Any]]) -> tuple[list[dict], list[dict], list[dict]]:
        vod_list, photo_list, live_list = [], [], []

        for item in contents:
            media = item.get("media")
            if not media:
                raise ValueError("The 'media' field is missing in the media item")

            if not self._is_within_time_range(media.get("publishedAt")):
                continue

            match self._classify_media(media):
                case "VOD":
                    vod_list.append(media)
                case "PHOTO":
                    photo_list.append(media)
                case "LIVE":
                    live_list.append(media)

        return vod_list, photo_list, live_list

    def fanclub_items(self, contents: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        fanclub: list[dict] = []
        not_fanclub: list[dict] = []
        for item in contents:
            match item.get("isFanclubOnly"):
                case True:
                    fanclub.append(item)
                case False:
                    not_fanclub.append(item)
                case _:
                    not_fanclub.append(item)
        return fanclub, not_fanclub

    async def _extract_pagination(self, _data: dict[str, Any]) -> tuple[str | None, bool]:
        pagination: dict[str, Any] = _data.get("data", {})
        cursor: str | None = pagination.get("cursor", {}).get("next")
        has_next: bool = pagination.get("hasNext", False)
        return cursor, has_next


class MediaFetcher:
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_name: str,
        time_a: datetime | None,
        time_b: datetime | None,
    ):
        self.community_id: int = community_id
        self.communityname: str = communityname
        self.MP: MediaParser = MediaParser(community_id, communityname, custom_name, time_a, time_b)

    @cached_property
    def LIVE(self) -> Live:
        return Live()

    @cached_property
    def MediaList(self) -> MediaList:
        return MediaList()

    def normalization(self, data: dict) -> dict:
        for item in data.get("data", {}).get("contents", []):
            media = item.get("media", {})
            media["communityArtists"] = item.get("communityArtists", [])
            item["media"] = media
        return data

    async def get_all_media_lists(
        self,
    ) -> tuple[list[dict], list[dict], list[dict]] | bool:
        vod_total: list[dict] = []
        photo_total: list[dict] = []
        live_total: list[dict] = []
        params: dict[str, Any] = await self._build_params(cursor=None)

        while True:
            media_data, live_data = await self._fetch_data(params)

            if not (media_data or live_data):
                self.error_printer(media_data, live_data)
                break

            # 並行解析 + build params
            (
                (vods, photos, params_media, has_next_media),
                (
                    lives,
                    params_live,
                    has_next_live,
                ),
            ) = await asyncio.gather(
                self._process_media_chunk(media_data),
                self._process_live_chunk(live_data),
            )
            vod_total.extend(vods)
            photo_total.extend(photos)
            live_total.extend(lives)

            if not (has_next_media or has_next_live):
                break

            # 合併下一輪要用的 params
            params = {
                "media": params_media,
                "live": params_live,
            }

        return vod_total, photo_total, live_total

    def error_printer(self, media_data: dict[str, Any], live_data: dict[str, Any]) -> None:
        if not media_data and live_data:
            M = "Media data"
        elif not live_data and media_data:
            M = "Live data"
        else:
            M = "Media and Live data"
            logger.warning(f"Fail to get 【{Color.fg('light_yellow')}{M}{Color.fg('gold')}】")

    async def _fetch_data(self, params: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        try:
            async with asyncio.TaskGroup() as tg:
                media_task = tg.create_task(self.MediaList.media_list(self.community_id, params, use_proxy))
                live_task = tg.create_task(self.LIVE.fetch_live_replay(self.community_id, params, use_proxy))
        except ExceptionGroup:
            return {}, {}

        media_data = media_task.result()
        live_data = live_task.result()
        return media_data, live_data

    async def _process_media_chunk(self, media_data: dict[str, Any]) -> tuple[list[VODMediaItem], list[PhotoMediaItem], dict[str, Any], bool]:
        media_data = self.normalization(media_data)
        vods, photos, _, cursor, has_next = await self.MP.parse(media_data)
        next_params: dict[str, Any] = await self._build_params(cursor)
        return vods, photos, next_params, has_next

    async def _process_live_chunk(self, live_data: dict[str, Any]) -> tuple[list[LiveMediaItem], dict[str, Any], bool]:
        live_data = self.normalization(live_data)
        _, _, lives, cursor, has_next = await self.MP.parse(live_data)
        next_params: dict[str, Any] = await self._build_params(cursor)
        return lives, next_params, has_next

    async def _build_params(self, cursor: str | None) -> dict[str, Any]:
        pagesize: int = 999999999
        params: dict[str, Any] = {"pageSize": pagesize, "languageCode": "en"}
        if cursor:
            params["next"] = cursor
        return params
