import asyncio
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple

from berrizdown.lib.artis.menu import Board
from berrizdown.lib.media_queue import MediaQueue
from berrizdown.mystate.parse_my import request_my
from berrizdown.static.color import Color
from berrizdown.static.parameter import paramstore
from berrizdown.unit.getall.GetMediaList import MediaFetcher
from berrizdown.unit.getall.GetNotifyList import NotifyFetcher
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import BerrizAPIClient
from berrizdown.unit.main_process import MediaProcessor
from berrizdown.unit.media.media_json_process import MediaJsonProcessor
from berrizdown.unit.user_choice import InquirerPySelector

logger = setup_logging("handle_choice", "light_slate_gray")


# Get the parameter flags with default False
liveonly = paramstore.get("liveonly")
mediaonly = paramstore.get("mediaonly")
photoonly = paramstore.get("photoonly")
boardonly = paramstore.get("board")
noticeonly = paramstore.get("noticeonly")
cmtonly = paramstore.get("cmtonly")


active_conditions_1 = sum(
    [
        bool(liveonly),
        bool(mediaonly),
        bool(photoonly),
    ]
)


active_conditions_2 = sum(
    [
        bool(boardonly),
        bool(noticeonly),
        bool(cmtonly),
    ]
)


active_conditions: int = sum(
    [
        bool(liveonly),
        bool(mediaonly),
        bool(photoonly),
        bool(boardonly),
        bool(noticeonly),
        bool(cmtonly),
    ]
)


class MediaLists(NamedTuple):
    vod_list: list[dict[str, Any]]
    photo_list: list[dict[str, Any]]
    live_list: list[dict[str, Any]]
    post_list: list[dict[str, Any]]
    notice_list: list[dict[str, Any]]
    cmt_list: list[dict[str, Any]]


class FilteredMediaLists(NamedTuple):
    filter_vod_list: list[dict[str, Any]]
    filter_photo_list: list[dict[str, Any]]
    filter_live_list: list[dict[str, Any]]
    filter_post_list: list[dict[str, Any]]
    filter_notice_list: list[dict[str, Any]]
    filter_cmt_list: list[dict[str, Any]]


SelectedMediaDict = dict[str, list[dict[str, Any]]]
ListDataTuple = tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]


class Handle_Choice:
    
    _BOARD_LABEL: dict[str, str] = {
        "filter_vod_list": "VOD",
        "filter_photo_list": "PHOTO",
        "filter_live_list": "LIVE",
        "filter_post_list": "POST",
        "filter_notice_list": "NOTICE",
        "filter_cmt_list": "CMT",
    }

    def __init__(
        self,
        community_id: int,
        community_name: str,
        custom_name: str | None = None,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ) -> None:
        self.community_id: int = community_id
        self.community_name: str = community_name
        self.custom_community_name: str | None = custom_name
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b
        self.selected_media: SelectedMediaDict | None = None
        self.fetcher = MediaFetcher(
            self.community_id,
            self.community_name,
            self.custom_community_name,
            self.time_a,
            self.time_b,
        )

    @property
    def _active_conditions_1(self) -> int:
        return sum(bool(paramstore.get(k)) for k in ("liveonly", "mediaonly", "photoonly"))

    @property
    def _active_conditions_2(self) -> int:
        return sum(bool(paramstore.get(k)) for k in ("board", "noticeonly", "cmtonly"))

    @property
    def _active_conditions(self) -> int:
        return self._active_conditions_1 + self._active_conditions_2

    async def get_list_data(self) -> MediaLists:
        board_result, media_result = await asyncio.gather(
            self._board_chunk(), self._media_chunk()
        )
        post_list, notice_list, cmt_list, board_type = board_result
        vod_list, photo_list, live_list = media_result
        match board_type:
            case "artist":
                if not paramstore.get("noticeonly"):
                    notice_list = []
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case "notice":
                return MediaLists(vod_list, photo_list, live_list, [], notice_list, [])
            case "notice+board":
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case "archive":
                paramstore._store["enable_archive"] = True
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case _:
                return MediaLists(vod_list, photo_list, live_list, [], [], [])

    async def _media_chunk(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        if self._active_conditions_1 != 0 or self._active_conditions == 0:
            return await self.fetcher.get_all_media_lists()
        return [], [], []

    async def _board_chunk(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
        data_list: list | list[list] = []
        board_type: str = ""
        post_list: list[dict[str, Any]] = []
        notice_list: list[dict[str, Any]] = []
        cmt_list: list[dict[str, Any]] = []

        board: Board = Board(
            self.community_id,
            self.community_name,
            self.custom_community_name,
            self.time_a,
            self.time_b,
        )
        if self._active_conditions_2 != 0 or self._active_conditions == 0:
            data_list, board_type = await board.get_artis_board_list()

        match board_type:
            case "artist":
                post_list = data_list
            case "notice":
                notice_list = data_list
            case "notice+board":
                post_list, notice_list = data_list[0], data_list[1]
            case "archive":
                post_list, cmt_list, notice_list = data_list[0], data_list[1], data_list[2]

        return post_list, notice_list, cmt_list, board_type

    async def fetch_filtered_media(self) -> FilteredMediaLists:
        media: MediaLists = await self.get_list_data()

        if self._active_conditions == 0:
            return FilteredMediaLists(
                media.vod_list,
                media.photo_list,
                media.live_list,
                media.post_list,
                media.notice_list,
                media.cmt_list,
            )

        return FilteredMediaLists(
            filter_vod_list=media.vod_list if paramstore.get("mediaonly") else [],
            filter_photo_list=media.photo_list if paramstore.get("photoonly") else [],
            filter_live_list=media.live_list if paramstore.get("liveonly") else [],
            filter_post_list=media.post_list if paramstore.get("board") else [],
            filter_notice_list=media.notice_list if paramstore.get("noticeonly") else [],
            filter_cmt_list=media.cmt_list if paramstore.get("cmtonly") else [],
        )

    async def _build_media_list(self) -> SelectedMediaDict | None:
        media: FilteredMediaLists = await self.fetch_filtered_media()

        self.print_chosen_boards(media)
        return await InquirerPySelector(
            media.filter_vod_list,
            media.filter_photo_list,
            media.filter_live_list,
            media.filter_post_list,
            media.filter_notice_list,
            media.filter_cmt_list,
        ).run()

    async def handle_choice(self) -> None:
        if paramstore.get("no_cookie") is not True:
            await request_my()

        if self.time_a is not None or self.time_b is not None:
            self.print_time_filter()

        self.selected_media: SelectedMediaDict | None = await self._build_media_list()
        if self.selected_media is None:
            logger.info(f"{Color.fg('apple_green')}Not found, exit{Color.reset()}")
            await BerrizAPIClient().close_session()
            return None

        self.print_user_chosen()
        await self.process_selected_media()

    def print_chosen_boards(self, media: FilteredMediaLists) -> None:
        active: list[tuple[str, list[dict[str, Any]]]] = [
            (label, lst)
            for key, lst in media._asdict().items()
            if (label := Handle_Choice._BOARD_LABEL[key]) and lst
        ]
        if active:
            label_str: str = "|".join(
                f"{Color.fg('yellow' if i % 2 == 0 else 'khaki')}{name}{Color.reset()}"
                for i, (name, _) in enumerate(active)
            )
            logger.info(f"Chosen boards: {label_str}")

    def print_user_chosen(self) -> None:
        if not self.selected_media:
            return
        media_types: list[tuple[str, str]] = [
            ("vods", "VOD"),
            ("photos", "PHOTO"),
            ("lives", "Live"),
            ("post", "Post"),
            ("notice", "Notice"),
            ("cmt", "CMT"),
        ]
        messages: list[str] = [
            f"{Color.fg('khaki')}{len(items)} {Color.fg('light_gray')}{label}"
            for key, label in media_types
            if (items := self.selected_media.get(key, []))
        ]
        if messages:
            logger.info(
                f"{Color.fg('light_gray')}Chosen: {', '.join(messages)}{Color.reset()}"
            )

    def print_time_filter(self) -> None:
        time_a = self.time_a.strftime("%Y-%m-%d %H:%M") if self.time_a else "—"
        time_b = self.time_b.strftime("%Y-%m-%d %H:%M") if self.time_b else "—"
        logger.info(
            f"{Color.fg('tomato')}Time filter "
            f"{Color.fg('sand')}{time_a} "
            f"{Color.fg('light_gray')}- "
            f"{Color.fg('sand')}{time_b}"
            f"{Color.reset()}"
        )

    async def process_selected_media(self) -> None:
        assert self.selected_media is not None
        processed_media: SelectedMediaDict = MediaJsonProcessor.process_selection(
            self.selected_media
        )
        dispatch: list[tuple[str, str]] = [
            ("vods", "VOD"),
            ("lives", "LIVE"),
            ("photos", "PHOTO"),
            ("post", "POST"),
            ("notice", "NOTICE"),
            ("cmt", "CMT"),
        ]
        for key, media_type in dispatch:
            if not self.selected_media.get(key):
                continue
            queue = MediaQueue()
            queue.enqueue_batch(processed_media[key], media_type)
            await MediaProcessor(
                {key: self.selected_media[key]},
                self.community_id,
                self.community_name,
            ).process_media_queue(queue)