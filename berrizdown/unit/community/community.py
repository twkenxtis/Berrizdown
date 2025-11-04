import sys
from typing import Any, TypedDict

try:
    from async_lru import alru_cache
except KeyboardInterrupt:
    raise KeyboardInterrupt("KeyboardInterrupt")

from berrizdown.lib.__init__ import use_proxy
from berrizdown.static.color import Color
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import BerrizAPIClient, Community, My

logger = setup_logging("community", "ivory")


class CommunityDict(TypedDict):
    communityKey: str
    communityId: int


MY: My = My()
CM: Community = Community()


async def init_cm_for_main(input: str | int):
    community = await get_community(input)
    if community is None:
        logger.error(f"{Color.fg('black')}Input Community ID invaild{Color.reset()} → {Color.fg('gold')}【{input}】")
        logger.info(f"{Color.fg('sea_green')}Use {Color.fg('gold')}--community {Color.fg('sea_green')}for more info!{Color.reset()}")
        await get_community_print()
        await BerrizAPIClient().close_session()
        sys.exit(1)
    else:
        return community


def search_community(contents: list[CommunityDict], query: str | int | None) -> str | int | None:
    if query is None:
        return None
    query = int(query) if isinstance(query, str) and query.isdigit() else query
    logger.debug(f"{Color.fg('gold')}search_community {query}, {type(query)}{Color.reset()}")
    if isinstance(query, str):
        q = query.strip().lower()
        for item in contents:
            key = item.get("communityKey", "").lower()
            if q == key:
                return item.get("communityId")

    elif isinstance(query, int):
        for item in contents:
            if item.get("communityId") == query:
                return item.get("communityKey")
    return None


# custom_dict 的回傳值可以是 str (對應的 key/value) 或 None
_cached_home_response: dict[str, Any] | None = None


async def custom_dict(input_str: str | int | None) -> str | None:
    if input_str is None:
        return None
    mapping: dict[str, str] = {}
    normalized = str(input_str).strip().lower()
    data = mapping.get(normalized)

    if data is None:
        match normalized:
            case "crushology101":
                return "Crushology 101"
            case "tempest":
                return "Tempest"
            case "ke_actors_audition":
                return "2025 Kakao Ent. Actors Audition"
            case "theballadofus":
                return "The Ballad of Us"
            case _:
                global _cached_home_response
                if _cached_home_response is None:
                    try:
                        resp = await MY.fetch_home(use_proxy)
                        if resp is None:
                            return None
                        if resp.get("code") != "0000":
                            return None
                        _cached_home_response = resp
                    except AttributeError:
                        return None

                merged_dict = {}
                for i in _cached_home_response["data"]["active"]:
                    name = i["title"]
                    communityId = str(i["communityId"])
                    communityKey = str(i["communityKey"])
                    kv = {communityKey: name, communityId: name}
                    merged_dict.update(kv)

                data = merged_dict.get(normalized)

    return data


# get_community 的回傳值是 str (communityKey) 或 int (communityId) 或 None
async def get_community(query: str | int | None = None) -> str | int | None:
    data = await request_community_community_keys()
    if data == {}:
        return None
    contents: list[CommunityDict] = data.get("data", {}).get("contents", [])
    result = search_community(contents, query)
    if isinstance(result, str):
        return result.strip()
    # 回傳 int communityId 或 None
    return result


async def get_community_print() -> None:
    data = await request_community_community_keys()
    if data == {}:
        return None

    contents: list[CommunityDict] = data.get("data", {}).get("contents", [])

    for i in contents:
        if "test" not in i.get("communityKey", "") and int(i.get("communityId")) < 9999999:
            Community_id: int | None = i.get("communityId")
            communityKey: str | None = i.get("communityKey")
            logger.info(f"{Color.fg('light_gray')}Community_id: {Color.fg('steel_blue')}{Community_id}, {Color.fg('light_gray')}communityKey: {Color.fg('plum')}{communityKey}")


@alru_cache(maxsize=1)
async def request_community_community_keys() -> dict[str, Any]:
    try:
        data: dict[str, Any] | None = await CM.community_keys(use_proxy)
        if data is None:
            return {}
        if data.get("code") == "0000":
            return data
        else:
            return {}
    except AttributeError:
        return {}
