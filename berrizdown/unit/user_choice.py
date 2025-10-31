import asyncio
import re
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from static.color import Color
from static.parameter import paramstore

from unit.community.community import custom_dict, get_community
from unit.handle.handle_log import setup_logging

logger = setup_logging("user_choice", "fresh_chartreuse")


MediaItem = dict[str, str | dict[str, Any] | bool]
SelectedMedia = dict[str, list[dict[str, Any]]]
Key = tuple[str, int]


class InquirerPySelector:
    def __init__(
        self,
        vod_list: list[dict[str, Any]],
        photo_list: list[dict[str, Any]],
        live_list: list[dict[str, Any]],
        post_list: list[dict[str, Any]],
        notice_list: list[dict[str, Any]],
        cmt_list: list[dict[str, Any]],
    ) -> None:
        self.vod_items = vod_list
        self.photo_items = photo_list
        self.live_items = live_list
        self.post_items = post_list
        self.notice_list = notice_list
        self.cmt_list = cmt_list

    def _filter_items_by_title_regex(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raw_value = paramstore.get("retitle")
        match raw_value:
            case None:
                cleaned = ""
            case _:
                if raw_value.startswith("r"):
                    raw_value = raw_value[1:]
                if raw_value.startswith(("'", '"')) and raw_value.endswith(("'", '"')):
                    raw_value = raw_value[1:-1]
                cleaned = raw_value
        pattern: str | None = rf"{cleaned}"
        if not pattern:
            return items

        compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return [item for item in items if compiled.search(item.get("title", ""))]

    def filter_all_by_regex(self) -> None:
        self.vod_items = self._filter_items_by_title_regex(self.vod_items)
        self.photo_items = self._filter_items_by_title_regex(self.photo_items)
        self.live_items = self._filter_items_by_title_regex(self.live_items)
        self.post_items = self._filter_items_by_title_regex(self.post_items)
        self.notice_list = self._filter_items_by_title_regex(self.notice_list)
        self.cmt_list = self._filter_items_by_title_regex(self.cmt_list)

    async def _populate_entries(self) -> list[tuple[str, int, dict[str, Any]]]:
        """Populate entries from all item lists concurrently."""
        entries: list[tuple[str, int, dict[str, Any]]] = []
        try:
            await asyncio.gather(
                asyncio.to_thread(lambda: [entries.append(("vod", idx, item)) for idx, item in enumerate(self.vod_items)]),
                asyncio.to_thread(lambda: [entries.append(("photo", idx, item)) for idx, item in enumerate(self.photo_items)]),
                asyncio.to_thread(lambda: [entries.append(("live", idx, item)) for idx, item in enumerate(self.live_items)]),
                asyncio.to_thread(lambda: [entries.append(("post", idx, item)) for idx, item in enumerate(self.post_items)]),
                asyncio.to_thread(lambda: [entries.append(("notice", idx, item)) for idx, item in enumerate(self.notice_list)]),
                asyncio.to_thread(lambda: [entries.append(("cmt", idx, item)) for idx, item in enumerate(self.cmt_list)]),
            )
        except TypeError as e:
            if str(e) == "'NoneType' object is not iterable":
                logger.info("No items")
                return []
        entries.sort(key=lambda x: x[2]["publishedAt"])
        return entries

    async def _build_item_choices(self, entries: list[tuple[str, int, dict[str, Any]]]) -> tuple[dict[int, tuple[str, int]], list[Choice]]:
        """Build display map and item choices from entries."""
        display_map: dict[int, tuple[str, int]] = {}
        item_choices: list[Choice] = []

        for disp_no, (t, idx, item) in enumerate(entries, start=1):
            display_map[disp_no] = (t, idx)
            core: str = format_core(item, t)
            prefix: str = "|Fanclub|" if item.get("isFanclubOnly") else "|Not Fanclub|"
            community_name = await custom_dict(await get_community(item.get("communityId")))
            if community_name is None:
                community_name: str = f"{await get_community(item.get('communityId'))}"
            else:
                community_name: str = f"{community_name}"
            ts: str = await convert_to_korea_time(item["publishedAt"])
            match core:
                case "NOTICE-NO-INFO":
                    name = f"{disp_no:6d} {ts} {community_name} {prefix} {t.upper():6s} {item['title']} "
                case _:
                    name = (f"{disp_no:6d} {ts} {community_name} {prefix} {t.upper():6s} {core} | {item['title']}").replace("'", "").replace("(", "").replace(")", "")
            item_choices.append(Choice(value=disp_no, name=name))

        return display_map, item_choices

    async def _handle_range_selection(self, item_choices: list[Choice], display_map: dict[int, tuple[str, int]]) -> set[int]:
        """Handle range/checkbox selection with quick select commands."""
        # Build quick select choices for the checkbox menu
        quick_select_choices: list[Choice] = [
            Choice("all", name="(All VOD | Photos | Live | POST | NOTICE | CMT)"),
            Choice("vall", name="(All VOD)"),
            Choice("pall", name="(All Photos)"),
            Choice("lall", name="(All Live)"),
            Choice("ball", name="(All POST)"),
            Choice("nall", name="(All NOTICE)"),
            Choice("ccall", name="(All CMT)"),
        ]

        # Show checkbox with quick commands + individual items
        selected: list[str | int] = await inquirer.checkbox(
            message="Finalize your selection (→ all, ← none, type to filter):",
            choices=quick_select_choices + item_choices,
            cycle=True,
            height=30,
            border=True,
            validate=lambda res: len(res) > 0 or "",
            keybindings={
                "toggle-all-true": [{"key": "right"}],
                "toggle-all-false": [{"key": "left"}],
            },
            instruction="→ select all, ← deselect all",
            transformer=lambda res: f"{' '.join(map(lambda x: str(x).strip(), res))}",
        ).execute_async()

        # Process selections
        picks: set[int] = set()
        for item in selected:
            if item == "all":
                picks.update(display_map.keys())
            elif item == "vall":
                picks.update({n for n, (t, _) in display_map.items() if t == "vod"})
            elif item == "pall":
                picks.update({n for n, (t, _) in display_map.items() if t == "photo"})
            elif item == "lall":
                picks.update({n for n, (t, _) in display_map.items() if t == "live"})
            elif item == "ball":
                picks.update({n for n, (t, _) in display_map.items() if t == "post"})
            elif item == "nall":
                picks.update({n for n, (t, _) in display_map.items() if t == "notice"})
            elif item == "ccall":
                picks.update({n for n, (t, _) in display_map.items() if t == "cmt"})
            elif isinstance(item, int):
                picks.add(item)

        return picks

    async def run(self) -> SelectedMedia | None:
        self.filter_all_by_regex()

        entries = await self._populate_entries()
        if not entries:
            return None

        display_map, item_choices = await self._build_item_choices(entries)

        if not item_choices:
            logger.info("No items found")
            return None

        # Create quick command choices (only range option now)
        quick_commands: list[Choice] = [
            Choice("range", name="[Custom — manual select]"),
        ]

        # Initial selection with fuzzy search
        try:
            cmd: str | int = await inquirer.fuzzy(
                message="Select items or quick command:",
                choices=quick_commands + item_choices,
                default="",
                cycle=False,
                border=True,
            ).execute_async()
        except KeyboardInterrupt:
            logger.info(f"Program interrupted: {Color.fg('light_gray')}User canceled{Color.reset()}")
            sys.exit(0)

        picks: set[int] = set()
        if cmd == "range":
            # Enter secondary menu with all commands + checkbox
            picks = await self._handle_range_selection(item_choices, display_map)
        else:
            # Single item selection
            picks = {cmd} if isinstance(cmd, int) else set()

        return await self._collect(picks, display_map)

    async def _collect(self, picks: set[int], display_map: dict[int, tuple[str, int]]) -> SelectedMedia:
        try:
            vods: list[dict[str, Any]] = [self.vod_items[idx] for n in picks if (t := display_map[n])[0] == "vod" for idx in [t[1]]]
            photos: list[dict[str, Any]] = [self.photo_items[idx] for n in picks if (t := display_map[n])[0] == "photo" for idx in [t[1]]]
            lives = []
            for n in picks:
                if (t := display_map[n])[0] == "live":
                    item = self.live_items[t[1]]
                    if item.get("live", {}).get("liveStatus") == "REPLAY":
                        lives.append(item)
                    else:
                        logger.warning(
                            f"{Color.fg('turquoise')}{await custom_dict(await get_community(item.get('communityId')))} "
                            f"{Color.fg('light_magenta')}{item.get('title', 'Unknown Title')} "
                            f"{Color.fg('light_gray')}had no replay, try again later{Color.reset()}"
                            f"{Color.fg('gold')} Skip it.{Color.reset()}"
                        )
            post: list[dict[str, Any]] = [self.post_items[idx] for n in picks if (t := display_map[n])[0] == "post" for idx in [t[1]]]
            notice: list[dict[str, Any]] = [self.notice_list[idx] for n in picks if (t := display_map[n])[0] == "notice" for idx in [t[1]]]
            cmt: list[dict[str, Any]] = [self.cmt_list[idx] for n in picks if (t := display_map[n])[0] == "cmt" for idx in [t[1]]]
            return {
                "vods": vods,
                "photos": photos,
                "lives": lives,
                "post": post,
                "notice": notice,
                "cmt": cmt,
            }
        except KeyError:
            return {
                "vods": [],
                "photos": [],
                "lives": [],
                "post": [],
                "notice": [],
                "cmt": [],
            }


async def convert_to_korea_time(iso_string_utc: str) -> str:
    dt_utc: datetime = datetime.fromisoformat(iso_string_utc.replace("Z", "+00:00"))
    dt_kst: datetime = dt_utc.astimezone(ZoneInfo("Asia/Seoul"))
    formatted_string: str = dt_kst.strftime("%y%m%d_%H:%M")
    return formatted_string


def format_core(item: dict[str, Any], t: str) -> str:
    try:
        if t == "vod":
            return f"{item['vod']['duration'] / 60:.1f}min"
        elif t == "photo":
            return f"{item['photo']['imageCount']} imgs"
        elif t == "live":
            match item["live"]["liveStatus"]:
                case "REPLAY":
                    return f"{item['live']['replay']['duration'] / 60:.1f}min, [Live, {item['communityArtists'][0]['name']}]"
                case "END":
                    return "NO-Replay"
        elif t == "post" and item.get("imageInfo"):
            image_count: str = f"{len(item.get('imageInfo')[1])}"
            match image_count:
                case "0":
                    return f"POST-ONLY, [{item['index']['boardInfo']['name']}, {item['writer_name']}]"
                case _:
                    return f" ({image_count} imgs), [{item['index']['boardInfo']['name']}, {item['writer_name']}]"
        elif t == "notice":
            return "NOTICE-NO-INFO"
        elif t == "cmt":
            if item.get("imageCount", 0) > 0:
                return f"COMMENT, ({item['imageCount']} imgs), [{item['board']['boardName']}, {item['userNickname']}]"
            return f"COMMENT, [{item['board']['boardName']}, {item['userNickname']}]"
    except TypeError:
        return ""
    return "unknown"
