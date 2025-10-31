import asyncio
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple

from lib.artis.menu import Board
from lib.media_queue import MediaQueue
from mystate.parse_my import request_my
from static.color import Color
from static.parameter import paramstore
from unit.getall.GetMediaList import MediaFetcher
from unit.getall.GetNotifyList import NotifyFetcher
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import BerrizAPIClient
from unit.main_process import MediaProcessor
from unit.media.media_json_process import MediaJsonProcessor
from unit.user_choice import InquirerPySelector

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
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_name: str,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ):
        self.custom_communityname: str = custom_name
        self.community_id: int = community_id
        self.communityname: str = communityname
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b
        self.selected_media = None
        self.fetcher = MediaFetcher(self.community_id, self.communityname, custom_name, self.time_a, self.time_b)

    async def get_list_data(self) -> ListDataTuple:
        # Fetch all media lists concurrently
        TYPE: str = ""
        MediaLists([], [], [], [], [], [])
        post_list: list[dict[str, Any]] = []
        notice_list: list[dict[str, Any]] = []
        cmt_list: list[dict[str, Any]] = []
        board_result, media_result = await asyncio.gather(self._board_chunk(), self._media_chunk())
        post_list, notice_list, cmt_list, TYPE = board_result
        vod_list, photo_list, live_list = media_result

        match TYPE:
            case "artist":
                if noticeonly is False:
                    notice_list: list[dict[str, Any]] = []
                    return MediaLists(
                        vod_list,
                        photo_list,
                        live_list,
                        post_list,
                        notice_list,
                        cmt_list,
                    )
            case "notice":
                post_list: list[dict[str, Any]] = []
                cmt_list: list[dict[str, Any]] = []
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case "notice+board":
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case "archive":
                paramstore._store["enable_archive"] = True
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)
            case _:
                post_list, cmt_list, notice_list = [], [], []
                return MediaLists(vod_list, photo_list, live_list, post_list, notice_list, cmt_list)

    async def _media_chunk(self) -> tuple[list[dict], list[dict], list[dict]]:
        if active_conditions_1 != 0 or active_conditions_1 + active_conditions_2 == 0:
            vod_list, photo_list, live_list = await self.fetcher.get_all_media_lists()
        else:
            vod_list, photo_list, live_list = [], [], []
        return vod_list, photo_list, live_list

    async def _board_chunk(self) -> tuple[list[dict], list[dict], list[dict], str]:
        cmt_list: list[dict[str, Any]] = []
        post_list, notice_list = [], []
        TYPE: str = ""
        BO: Board = Board(
            self.community_id,
            self.communityname,
            self.custom_communityname,
            self.time_a,
            self.time_b,
        )
        if active_conditions_2 != 0 or active_conditions_1 + active_conditions_2 == 0:
            data_list, TYPE = await BO.get_artis_board_list()
        match TYPE:
            case "artist":
                post_list = data_list
                notice_list = []
            case "notice":
                post_list = []
                notice_list = data_list
            case "notice+board":
                post_list = data_list[0]
                notice_list = data_list[1]
            case "archive":
                post_list = data_list[0]
                cmt_list = data_list[1]
                notice_list = data_list[2]
        return post_list, notice_list, cmt_list, TYPE

    async def fetch_filtered_media(self) -> ListDataTuple:
        # 接收 ListDataTuple, 5個 List[dict]
        (
            vod_list,
            photo_list,
            live_list,
            post_list,
            notice_list,
            cmt_list,
        ) = await self.get_list_data()
        # If no conditions are True, return all lists
        if active_conditions == 0:
            return vod_list, photo_list, live_list, post_list, notice_list, cmt_list
        # Initialize result lists based on corresponding flags
        result_vod_list: list[dict[str, Any]] = vod_list if mediaonly else []
        result_photo_list: list[dict[str, Any]] = photo_list if photoonly else []
        result_live_list: list[dict[str, Any]] = live_list if liveonly else []
        result_post_list: list[dict[str, Any]] = post_list if boardonly else []
        result_notice_list: list[dict[str, Any]] = notice_list if noticeonly else []
        result_cmt_list: list[dict[str, Any]] = cmt_list if cmtonly else []
        return FilteredMediaLists(
            result_vod_list,
            result_photo_list,
            result_live_list,
            result_post_list,
            result_notice_list,
            result_cmt_list,
        )

    async def handle_choice(self) -> SelectedMediaDict | None:
        if paramstore.get("no_cookie") is not True:
            await request_my()

        if self.time_a is not None or self.time_b is not None:
            self.printer_time_filter()
        selected_media: SelectedMediaDict | None = await self.media_list()
        if selected_media is None:
            logger.info(f"{Color.fg('apple_green')}Not found, exit{Color.reset()}")
            await BerrizAPIClient().close_session()
        self.selected_media = await self.user_selected_media(selected_media)
        self.printer_user_choese()
        return await self.process_selected_media()

    def user_selected_board(
        self,
        filter_vod_list,
        filter_photo_list,
        filter_live_list,
        filter_post_list,
        filter_notice_list,
        filter_cmt_list,
    ) -> None:
        temp_list = []

        board_map = {
            "VOD": filter_vod_list,
            "PHOTO": filter_photo_list,
            "LIVE": filter_live_list,
            "POST": filter_post_list,
            "NOTICE": filter_notice_list,
            "CMT": filter_cmt_list,
        }

        for name, value in board_map.items():
            if value:
                temp_list.append(name)
        if temp_list != []:
            logger.info("Choese boards: " + "|".join(f"{Color.fg('yellow' if i % 2 == 0 else 'khaki')}{name}{Color.reset()}" for i, (name, value) in enumerate(board_map.items()) if value))

    async def media_list(self):
        # 接收 ListDataTuple, 6個 List[dict]
        filter_media = await self.fetch_filtered_media()
        (
            filter_vod_list,
            filter_photo_list,
            filter_live_list,
            filter_post_list,
            filter_notice_list,
            filter_cmt_list,
        ) = filter_media

        if paramstore.get("notify_mod") is True:
            # notify_only
            filter_live_list = await NotifyFetcher().get_all_notify_lists(self.time_a, self.time_b)
            (
                filter_vod_list,
                filter_photo_list,
                filter_post_list,
                filter_notice_list,
                filter_cmt_list,
            ) = (
                [],
                [],
                [],
                [],
                [],
            )
        self.user_selected_board(
            filter_vod_list,
            filter_photo_list,
            filter_live_list,
            filter_post_list,
            filter_notice_list,
            filter_cmt_list,
        )
        selected_media = await InquirerPySelector(
            filter_vod_list,
            filter_photo_list,
            filter_live_list,
            filter_post_list,
            filter_notice_list,
            filter_cmt_list,
        ).run()
        return selected_media

    async def user_selected_media(self, selected_media: dict[str, list[dict[str, Any]]]) -> SelectedMediaDict:
        if selected_media is None:
            sys.exit(0)
        self.selected_media = selected_media
        return self.selected_media

    def printer_user_choese(self):
        temp_messages = []
        media_types = [
            {"key": "vods", "color": "khaki", "label": "VOD"},
            {"key": "photos", "color": "khaki", "label": "PHOTO"},
            {"key": "lives", "color": "khaki", "label": "Live"},
            {"key": "post", "color": "khaki", "label": "Post"},
            {"key": "notice", "color": "khaki", "label": "Notice"},
            {"key": "cmt", "color": "khaki", "label": "CMT"},
        ]
        for media in media_types:
            selected_list = self.selected_media.get(media["key"], [])
            if len(selected_list) > 0:
                count = len(selected_list)
                color_name = media["color"]
                label = media["label"]

                formatted_item = f"{Color.fg(color_name)}{count} {Color.fg('light_gray')}{label}"
                temp_messages.append(formatted_item)
        if temp_messages:
            combined_message = ", ".join(temp_messages)
            logger.info(f"{Color.fg('light_gray')}choese {combined_message}{Color.reset()}")

    def printer_time_filter(self):
        logger.info(f"{Color.fg('tomato')}choese {Color.fg('sand')}{self.time_a} {Color.fg('light_gray')}- {Color.fg('sand')}{self.time_b}{Color.reset()}")

    async def process_selected_media(self) -> None:
        processed_media: SelectedMediaDict = MediaJsonProcessor.process_selection(self.selected_media)
        custom_media_types = [
            ("vods", "VOD"),
            ("lives", "LIVE"),
            ("photos", "PHOTO"),
            ("post", "POST"),
            ("notice", "NOTICE"),
            ("cmt", "CMT"),
        ]
        for k, type in custom_media_types:
            if self.selected_media.get(k):
                current_media_data = {k: self.selected_media[k]}
                MP: Callable = MediaProcessor(current_media_data, self.community_id, self.communityname).process_media_queue
                queue: MediaQueue = MediaQueue()
                queue.enqueue_batch(processed_media[k], type)
                await MP(queue)
