import asyncio
import sys
from datetime import datetime
from functools import cached_property
from typing import Any

from InquirerPy import inquirer
from lib.__init__ import use_proxy
from lib.artis.artis_archive import Archive
from static.api_error_handle import api_error_handle
from static.color import Color
from static.parameter import paramstore
from unit.cmt.cmt import CMT
from unit.handle.handle_board_from import BoardMain, BoardNotice
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Arits, Community

logger = setup_logging("menu", "ivory")


boardonly: bool | None = paramstore.get("board")
noticeonly: bool | None = paramstore.get("noticeonly")
cmtonly: bool | None = paramstore.get("cmtonly")


class Board_ERROR_Hanldle:
    @classmethod
    def board_error_handle(cls, json_data: dict[str, Any], boards_name: str) -> None:
        try:
            if json_data["code"] != "0000":
                logger.warning(f"Fail to get 【{Color.fg('light_yellow')}{boards_name}{Color.fg('gold')}】 {api_error_handle(json_data['code'])}")
                return []
        except KeyError:
            logger.warning(f"Fail to get 【{Color.fg('light_yellow')}{boards_name}{Color.fg('gold')}】")
            pass


class Board:
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_communityname: str,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ) -> None:
        self.custom_communityname: str = custom_communityname
        self.communityid: int = community_id
        self.communityname = communityname
        self.json_data: dict[str, Any] | None = None
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b

    @cached_property
    def Arits(self) -> "Arits":
        return Arits()

    @cached_property
    def Community(self) -> "Community":
        return Community()

    @cached_property
    def cmt(self) -> "CMT":
        return CMT(self.communityid, self.communityname)

    async def match_noticeonly(self, choices: list[dict[str, Any]]) -> list[dict[str, Any] | None]:
        match choices:
            case []:
                return {
                    "type": "board",
                    "iconType": "artist",
                    "id": "",
                    "name": "Unable to automatically select",
                }, []
            case _:
                selected_list = []
                selected: dict[str, Any] | None = None
                choices = [c for c in choices]
                filterchoice = [c for c in choices if c["value"]["type"] != "notice"]
                if filterchoice != []:
                    selected_notice = self.selected_notice(choices)
                    if noticeonly is True and boardonly is False and cmtonly is False:
                        selected_list.append(selected_notice)
                        selected = selected_notice
                    elif noticeonly == boardonly or noticeonly == cmtonly or boardonly == cmtonly:
                        selected_list.append(selected_notice)
                        try:
                            selected = await self.call_inquirer(filterchoice)
                            selected_list.append(selected)
                        except TimeoutError:
                            selected = await self.call_auto_choese(choices)
                            selected_list.append(selected)
                    else:
                        try:
                            selected = await self.call_inquirer(filterchoice)
                        except TimeoutError:
                            selected = await self.call_auto_choese(choices)
                    return selected, selected_list
                else:
                    return {
                        "type": "board",
                        "iconType": "artist",
                        "id": "",
                        "name": "Unable to automatically select",
                    }, []

    async def call_inquirer(self, filterchoice: list[dict]) -> dict:
        try:
            return await asyncio.wait_for(
                inquirer.select(
                    message="Please select a project: (After 3s auto choese default Options)",
                    choices=filterchoice,
                ).execute_async(),
                timeout=3,
            )
        except KeyboardInterrupt:
            logger.info(f"Program interrupted: {Color.fg('light_gray')}User canceled{Color.reset()}")
            sys.exit(0)

    async def call_auto_choese(self, choices: list[dict]) -> dict:
        for value in choices:
            if value["value"]["iconType"] == "artist":
                logger.info(f"{Color.fg('light_gray')}Auto-selecting default Options {Color.fg('light_blue')}{value['value']['name']}{Color.reset()}")
                selected = value["value"]
                return selected
        # 如我迴圈沒有符合條件返回模板預設
        return {
            "type": "board",
            "iconType": "artist",
            "id": "",
            "name": "Unable to automatically select",
        }

    def selected_notice(self, choices: list[dict]) -> dict:
        for value in choices:
            if "notice" in value["value"]["type"].lower():
                selected_notice = value["value"]
                return selected_notice

    def make_choice(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        new_menu = {
            "type": "board",
            "iconType": "archive",
            "id": "archive",
            "name": "Artis archive",
        }
        menus = data["data"].get("menus", [])
        menus.insert(0, new_menu)

        choice = [{"name": f"{idx}. {i['name']}", "value": i} for idx, i in enumerate(menus) if i["name"].lower() not in ("media", "live")]
        return choice

    async def get_artis_board_list(self) -> tuple[Any, str] | None:
        community_menu: dict[str, Any] | None = await self.Community.community_menus(self.communityid, use_proxy)

        if community_menu is None:
            return None
        selected, selected_list = await self.match_noticeonly(self.make_choice(community_menu))
        if selected is None:
            return None  # 如果沒有選擇，提前返回

        selected_list: list[dict[str:Any]]
        selected: dict[str]
        _type: str
        iconType: str
        _id: int | str
        name: str
        _type, iconType, _id, name = self.parse_user_select(selected)
        logger.info(f"【{name}】[{iconType}] （{_id}）")
        result_notice: list[dict[str]] = await self.handle_artist_notice(selected_list[0])
        return await self._get_artis_board_list(iconType, name, selected, selected_list, result_notice)

    async def _get_artis_board_list(
        self,
        iconType: str,
        name: str,
        selected: dict,
        selected_list: list,
        result_notice: list,
    ) -> tuple[Any, str] | None:
        if iconType not in ("artist", "artist-fanclub", "notice", "archive"):
            logger.warning(
                f"【{name}】{Color.reset()}{Color.fg('azure')} board type is {Color.fg('light_lemon')}experimental download function{Color.fg('azure')}{Color.fg('azure')} may experience download failures{Color.reset()}"
            )
        elif iconType == "archive":
            archive_post_list, archive_cmt = await self.handle_artist_archive()
            result = (archive_post_list, archive_cmt, result_notice)
            return (result, "archive")
        if len(selected_list) > 1:
            result: list[dict[str, Any]] = await self.handle_artist_board(selected)
            data = [result, result_notice]
            return (data, "notice+board")
        elif iconType in (
            "artist",
            "user",
            "artist-fanclub",
            "user-fanclub",
            "shop",
            "Shop",
            "SHOP",
            "event",
        ):
            result: list[dict[str, Any]] = await self.handle_artist_board(selected)
            return (result, "artist")
        elif iconType == "notice":
            result: list[dict[str, Any]] = await self.handle_artist_notice(selected)
            return (result, "notice")
        else:
            logger.warning(f"Fail to parse {Color.bg('magenta')}{iconType}{Color.reset()}{Color.fg('light_gray')}  {selected}")

    def parse_user_select(self, selected: dict[str, Any]) -> tuple[str, str, int | str, str]:
        _type: str = selected["type"]
        iconType: str = selected["iconType"]
        _id: int | str = selected["id"]
        name: str = selected["name"]
        return _type, iconType, _id, name

    async def handle_artist_board(self, selected: dict[str, Any]) -> list[dict[str, Any]]:
        board_list: list[dict[str, Any]] | None = await self.sort_board_list(selected)
        return await BoardMain(board_list, self.time_a, self.time_b).main()

    async def handle_artist_archive(self) -> tuple[list[dict], list[dict]]:
        AC: Archive = Archive(
            self.communityid,
            self.communityname,
            self.custom_communityname,
            self.time_a,
            self.time_b,
        )
        post_list, __archive_cmt = await AC.archive()
        archive_post_list = await BoardMain(post_list, self.time_a, self.time_b).main()
        if paramstore.get("cmtonly") is False:
            archive_cmt = []
        else:
            archive_cmt = await self.cmt.normalization(__archive_cmt)
        return archive_post_list, archive_cmt

    async def handle_artist_notice(self, selected: dict[str, Any]) -> list[dict[str, Any]]:
        if paramstore.get("fanclub") is True:
            logger.info("No Notice in Fanclub skip")
            return []
        board_list: list[dict[str, Any]] | None = await self.sort_board_list(selected)
        return await BoardNotice(board_list, self.communityid, self.time_a, self.time_b).notice_list()

    async def sort_board_list(self, data: dict[str, Any]) -> list[dict[str, Any]] | None:
        boards_id: int | str = data.get("id", "")
        boards_name: int | str = data.get("name", "")
        if data.get("type") in ("board", "shop", "event", "Event", "SHOP", "Shop"):
            return await self.get_all_board_content_lists(str(boards_id), str(boards_name))
        elif data.get("type") == "notice":
            return await Notice(self.communityid, self.communityname, self.custom_communityname).get_all_notice_content_lists()
        return None

    def basic_sort_json(self) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        if not self.json_data:
            return [], {}, False

        data: dict[str, Any] = self.json_data.get("data", {})
        cursor: dict[str, Any] | None = data.get("cursor")
        hasNext: bool = data.get("hasNext", False)
        contents: list[dict[str, Any]] = data.get("contents", [])
        params: dict[str, Any] = self.build_params(cursor)
        return contents, params, hasNext

    def build_params(self, cursor: dict[str, Any] | None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageSize": 100, "languageCode": "en"}
        if cursor and "next" in cursor:
            params["next"] = cursor["next"]
        return params

    async def get_all_board_content_lists(self, boards_id: str, boards_name: str) -> list[dict[str, Any]]:
        all_contents: list[dict[str, Any]] = []
        hasNext: bool = True

        # 初始請求
        params: dict[str, str | int] = {"pageSize": 100, "languageCode": "en"}
        self.json_data = await self._fetch_board_data(boards_id, params)
        contents: list[dict[str, Any]]
        contents, params, hasNext = self.basic_sort_json()
        all_contents.extend(contents)
        Board_ERROR_Hanldle.board_error_handle(self.json_data, boards_name)
        if not hasNext:
            return self.deduplicate_contents(all_contents)
        # 取得初始 next_int
        count: int = 0
        # 單筆擴展，每次用回應的指針
        while hasNext:
            result: dict[str, Any] | None = await self._fetch_board_data(boards_id, params)
            if result is None:
                break

            self.json_data = result
            page_contents: list[dict[str, Any]]
            page_contents, params, hasNext = self.basic_sort_json()
            if page_contents:
                all_contents.extend(page_contents)

            count += 1
            if count in range(499, 501):
                logger.warning("Over 500 pages, will take a long time to finish.")
            elif count == 50:
                logger.info(f"{Color.fg('light_gray')}Over{Color.fg('gold')} 50 {Color.reset()}{Color.fg('light_gray')}pages, will take a long time to finish.")
                logger.info(
                    f"{Color.fg('azure')} Try use command "
                    f"{Color.fg('light_lemon')}--spider , --crawler{Color.fg('azure')}"
                    f"{Color.fg('azure')} to unlock none max retries limit{Color.reset()}"
                    f"{Color.fg('cyan')} for long time fetch data ...{Color.reset()}"
                )
            elif count >= 100 and (count - 100) % 25 == 0:
                logger.info(f"{Color.fg('light_gray')}Fetch {Color.fg('gold')}{count}{Color.fg('light_gray')} pages, please wait...{Color.reset()}")
        return self.deduplicate_contents(all_contents)

    def deduplicate_contents(self, contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set = set()
        deduped: list[dict[str, Any]] = []
        for item in contents:
            post: dict[str, Any] = item.get("post", {})
            post_id: str | int | None = post.get("postId")
            if post_id is not None and post_id not in seen:
                seen.add(post_id)
                deduped.append(item)
        return deduped

    async def _fetch_board_data(self, boards_id: str, params: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] | None = await self.Arits._board_list(boards_id, str(self.communityid), params, use_proxy)
        return data if data is not None else {}


class Notice(Board):
    def __init__(self, community_id: int, communityname: str, custom_communityname: str) -> None:
        super().__init__(community_id, communityname, custom_communityname)

    async def fetch_notice_content_lists(self, params: dict[str, Any]) -> dict[str, Any] | None:
        return await self.Arits.request_notice(self.communityid, params, use_proxy)

    async def get_all_notice_content_lists(self) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "languageCode": "en",
            "pageSize": 999999999339134974,
        }
        all_contents: list[dict[str, Any]] = []
        hasNext: bool = True
        next_int: int | None = 0

        # 初始請求
        result: dict[str, Any] | None = await self.fetch_notice_content_lists(params)

        if result is None:
            return all_contents

        self.json_data = result
        contents: list[dict[str, Any]]
        contents, _, hasNext = self.basic_sort_json()
        all_contents.extend(contents)
        Board_ERROR_Hanldle.board_error_handle(self.json_data, "NOTICE")
        if not hasNext:
            return all_contents

        # 取得初始 next_int
        cursor: dict[str, Any] = self.json_data.get("data", {}).get("cursor", {})
        next_int = cursor.get("next", 0)

        # 單筆擴展，每次用回應的指針
        while hasNext and next_int is not None:
            params = {
                "pageSize": 999999999339134974,
                "languageCode": "en",
                "next": next_int,
            }
            result = await self.fetch_notice_content_lists(params)

            if result is None:
                break

            self.json_data = result
            page_contents: list[dict[str, Any]]
            page_contents, _, hasNext = self.basic_sort_json()

            actual_cursor: dict[str, Any] = result.get("data", {}).get("cursor", {})
            actual_next: int | None = actual_cursor.get("next", None)

            if page_contents:
                all_contents.extend(page_contents)

            if actual_next:
                next_int = actual_next
            else:
                hasNext = False
        return all_contents
