import asyncio
import difflib
from datetime import datetime
from functools import cached_property
from typing import Any

from lib.__init__ import use_proxy
from static.api_error_handle import api_error_handle
from static.artisarchive import ArtistContent
from static.color import Color
from static.parameter import paramstore
from unit.getall.GetMediaList import FanClubFilter
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Arits

logger = setup_logging("artis_archive", "khaki")


class Board_ERROR_Hanldle:
    @classmethod
    def board_error_handle(cls, json_data: dict[str, Any]) -> None:
        try:
            if json_data["data"]["contents"] == []:
                if json_data["code"] == "0000":
                    logger.warning("No artis board contents available")
                else:
                    logger.warning(f"Fail to get {api_error_handle(json_data['code'])} No contents found.")
        except KeyError as e:
            logger.error(f"Fail to get {api_error_handle(json_data['code'])}, Keyerror: {e}")


class Archive:
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_communityname: str,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ):
        self.custom_communityname: str = custom_communityname
        self.community_id: int = community_id
        self.communityname: str = communityname
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b

    @cached_property
    def artisboard(self) -> "ArtisBoard":
        return ArtisBoard(
            self.community_id,
            self.communityname,
            self.custom_communityname,
            self.time_a,
            self.time_b,
        )

    async def archive(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        post, cmt = await self.artisboard.get_all_archive_content_lists()
        post_list = await Post(post, self.community_id).get_post_details()
        return post_list, cmt


class ArtisBoard:
    def __init__(
        self,
        community_id: int,
        communityname: str,
        custom_communityname: str,
        time_a: datetime | None = None,
        time_b: datetime | None = None,
    ) -> None:
        self.communityid: int = community_id
        self.communityname: str = communityname or custom_communityname
        self.custom_communityname: str = custom_communityname or communityname
        self.time_a: datetime | None = time_a
        self.time_b: datetime | None = time_b

    @cached_property
    def artis(self) -> Arits:
        return Arits()

    @cached_property
    def FanClubFilter(self) -> FanClubFilter:
        return FanClubFilter()

    async def get_all_artis_id(self) -> list[str]:
        """獲取所有CM artis ID List"""
        data: dict[str, Any] | None = await self.artis.artis_list(self.communityid, use_proxy)
        if data is not None:
            return [str(y.get("communityArtistId")) for y in data["data"]["communityArtists"]]
        return []

    async def _validate_and_apply_popup(self, artis_ids: list[str], raw_filter_ids: list[str]) -> list[str]:
        # 正規化外部輸入
        filter_ids = [fid.strip() for fid in raw_filter_ids if fid and fid.strip()]
        if not filter_ids:
            return artis_ids

        artis_set = set(str(aid) for aid in artis_ids)
        validated = [fid for fid in filter_ids if fid in artis_set]
        return validated

    def empty_warrning(self, text: str) -> None:
        logger.info(f"No {text} board contents available")

    async def get_all_archive_content_lists(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """入口"""
        artis_ids: list[str] = await self.get_all_artis_id()
        is_fanclub: bool = await self._apply_fanclub_filter_once()
        try:
            raw_filter_ids: list[str] = paramstore.get("artisid")[0].split(",")
        except (TypeError, IndexError):
            raw_filter_ids = [""]
        if raw_filter_ids != [""]:
            logger.info(f"{Color.fg('ivory')}Filter artis id: {raw_filter_ids}{Color.reset()}")
        artis_ids = await self._validate_and_apply_popup(artis_ids, raw_filter_ids)
        merged_contents = await self._fetch_all_artis_contents(artis_ids)
        filtered_contents = self._filter_fanclub_contents(merged_contents, is_fanclub)

        post_list, comment_list = self.post_cmt_list_spilt(filtered_contents)
        if post_list == []:
            self.empty_warrning("post")
        if comment_list == []:
            self.empty_warrning("comment")
        return post_list, comment_list

    def post_cmt_list_spilt(self, input_list: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        post_list: list[dict[str, Any]] = []
        comment_list: list[dict[str, Any]] = []

        for item in input_list:
            if item.get("contentType") == "POST":
                post_list.append(item)
            elif item.get("contentType") == "CMT":
                comment_list.append(item)

        post_list = self.filter_by_time(post_list)
        comment_list = self.filter_by_time(comment_list)
        return post_list, comment_list

    def filter_by_time(self, input_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        should_filter: bool = isinstance(self.time_a, datetime) and isinstance(self.time_b, datetime)

        for index in input_list:
            ISO8601: str | None = ArtistContent(index).created_at
            if should_filter and ISO8601:
                try:
                    published_at: datetime = datetime.fromisoformat(ISO8601.replace("Z", "+00:00"))
                    if not (self.time_a <= published_at <= self.time_b):
                        continue
                except (ValueError, TypeError):
                    continue
            filtered.append(index)
        return filtered

    async def _apply_fanclub_filter_once(self) -> bool:
        FCINFO: Any | None = await self.FanClubFilter.is_fanclub()
        if FCINFO is None:
            return False
        return difflib.SequenceMatcher(FCINFO, self.communityname.lower()).ratio() >= 0.8 or difflib.SequenceMatcher(FCINFO, self.custom_communityname.lower()).ratio() >= 0.75

    def _filter_fanclub_contents(self, contents: list[dict[str, Any]], is_fanclub: bool) -> list[dict[str, Any]]:
        """根據 FanClub 狀態過濾內容"""
        if paramstore.get("fanclub") is True:
            return [it for it in contents if it.get("board", {}).get("isFanclubOnly") is True]
        if is_fanclub:
            return contents
        return [it for it in contents if it.get("board", {}).get("isFanclubOnly") is False]

    async def _fetch_all_artis_contents(self, artis_ids: list[str]) -> list[dict[str, Any]]:
        """使用 Semaphore 並發抓取所有藝人的內容"""
        sem = asyncio.Semaphore(7)
        tasks: list[asyncio.Task] = [asyncio.create_task(self._runner(aid)) for aid in artis_ids]

        async def _gate(task: asyncio.Task):
            async with sem:
                return await task

        gated_results: list[list[dict[str, Any]]] = await asyncio.gather(*[_gate(t) for t in tasks], return_exceptions=False)

        # 合併所有結果
        return [item for batch in gated_results for item in batch]

    async def _runner(self, artis_id: str) -> list[dict[str, Any]]:
        """簡化的單一藝人內容抓取流程：第一頁 + 剩餘頁 + 合併"""
        first_page = await self._fetch_first_page(artis_id)
        first_contents, params, hasNext = self.parse_page(first_page)

        rest_contents = await self._fetch_remaining_pages(artis_id, params, hasNext)

        return first_contents + rest_contents

    async def _fetch_first_page(self, artis_id: str) -> dict[str, Any]:
        """僅抓取第一頁並返回原始回應"""
        params: dict[str, str | int] = {"pageSize": 99, "languageCode": "en"}
        page = await self._fetch_artis_data(params, artis_id)
        Board_ERROR_Hanldle.board_error_handle(page)
        return page

    async def _fetch_remaining_pages(self, artis_id: str, initial_params: dict[str, Any], initial_hasNext: bool) -> list[dict[str, Any]]:
        """抓取第一頁之後的所有剩餘頁面"""
        all_contents: list[dict[str, Any]] = []
        count: int = 0
        params = initial_params
        hasNext = initial_hasNext

        next_task: asyncio.Task | None = asyncio.create_task(self._fetch_artis_data(params, artis_id)) if hasNext else None

        while hasNext and next_task:
            page = await next_task
            if not page:
                logger.warning(f"artis_id={artis_id} fetch failed; stop this id early.")
                break

            Board_ERROR_Hanldle.board_error_handle(page)
            page_contents, params, hasNext = self.parse_page(page)
            all_contents.extend(page_contents)

            count += 1
            self._log_fetch_progress(artis_id, count)

            next_task = asyncio.create_task(self._fetch_artis_data(params, artis_id)) if hasNext else None

        return all_contents

    async def _fetch_artis_data(self, params: dict[str, Any], artis_id: str) -> dict[str, Any]:
        page: dict[str, Any] | None = await self.artis.arits_archive_with_cmartisId(self.communityid, artis_id, params, use_proxy)
        return page or {}

    def build_params(self, cursor: dict[str, Any] | None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageSize": 99, "languageCode": "en"}
        if cursor and "next" in cursor:
            params["next"] = cursor["next"]
        return params

    def parse_page(self, page: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        data: dict[str, Any] = page.get("data", {})
        cursor: dict[str, Any] | None = data.get("cursor")
        hasNext: bool = data.get("hasNext", False)
        contents: list[dict[str, Any]] = data.get("contents", [])
        params: dict[str, Any] = self.build_params(cursor)
        return contents, params, hasNext

    def _log_fetch_progress(self, artis_id: str, count: int) -> None:
        if count == 50:
            logger.info(f"[artis_id={artis_id}] over 50 pages; this will take time.")
        elif count >= 100 and (count - 100) % 25 == 0:
            logger.info(f"[artis_id={artis_id}] fetched {count} pages; please wait.")
        elif count in range(499, 501):
            logger.warning(f"[artis_id={artis_id}] over 500 pages; very long run.")


class Post:
    def __init__(self, data: list[dict[str, Any]], community_id: int) -> None:
        self.community_id: int = community_id
        self.data: list[dict[str, Any]] = data

    @cached_property
    def artis(self) -> "Arits":
        return Arits()

    def _get_post_ids(self) -> list[str]:
        post_ids: list[str] = []
        for item in self.data:
            pid = item.get("postId")
            if isinstance(pid, str) and pid:
                post_ids.append(pid)
        return post_ids

    async def _fetch_detail(self, post_id: str) -> dict[str, Any] | None:
        try:
            response: dict[str, Any] | None = await self.artis.post_detil(self.community_id, post_id, use_proxy)
        except Exception as e:
            logger.error(f"Error fetching {post_id}: {e}")
            return None
        if response is None:
            return None
        if response.get("code") == "0000":
            return response.get("data")
        return None

    async def get_post_details(self) -> list[dict[str, Any]]:
        """
        1. Extract all post IDs
        2. Kick off all fetch tasks
        3. Collect results as they complete
        4. Return only successful data dicts
        """
        post_ids = self._get_post_ids()
        tasks = [asyncio.create_task(self._fetch_detail(pid)) for pid in post_ids]

        results: list[dict[str, Any]] = []
        for task in asyncio.as_completed(tasks):
            detail = await task
            if detail is not None:
                results.append(detail)

        return results
