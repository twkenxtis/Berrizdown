import asyncio
from typing import Never

from lib.interface.interface import Community_Uniqueness, StartProcess, URL_Parser, selected_media_list
from pydantic import HttpUrl
from unit.http.request_berriz_api import BerrizAPIClient

# main aiohttp session for all request
BAPIClient: BerrizAPIClient = BerrizAPIClient()


async def media_live() -> bool:
    # sample live uuid
    liveid: str = "019681ce-aa41-6af0-b423-1c1cc6894bc5"
    # all the vaild url for live
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/jsh/live/{liveid}/",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/jsh/live/{liveid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def media_video() -> bool:
    # sample media uuid
    mediaid: str = "0195cbb8-293a-43c4-f09f-9e04af1bbc2d"
    # all the vaild url for upload media
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/kiiikiii/media/content/{mediaid}/?mediaType=vod",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/kiiikiii/media/content/{mediaid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def media_image() -> bool:
    # sample photo uuid
    mediaid: str = "0198ebbe-208c-63fb-03e5-a5fee518f4be"
    # all the vaild url for images
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/kiiikiii/media/content/{mediaid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/kiiikiii/media/content/{mediaid}/",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def notice() -> bool:
    # sample notice id
    noticeid: int = 126
    # all the vaild url for notice
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/iu/notice/{noticeid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/iu/notice/{noticeid}/",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post() -> bool:
    # sample post uuid
    postid: str = "0195cbc2-7223-6105-adb8-88e819dd545d"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/kiiikiii/board/{boardid}/post/{postid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/kiiikiii/board/{boardid}/post/{postid}/",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_comment_last() -> bool:
    # sample post uuid
    postid: str = "0198bd54-98a4-6fe7-42fc-67923d1f14ff"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-comment
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?focus=comment"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/iu/board/{boardid}/post/{postid}/?focus=comment",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_artis() -> bool:
    # sample post uuid
    postid: str = "0199c97e-8cbf-ebd6-7952-ac1a68998050"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?reply=1759787",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/iu/board/{boardid}/post/{postid}/?reply=1759787",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_user2user() -> Never:
    # sample post uuid
    postid: str = "019a3860-2851-c927-0e6f-678dcf6424cc"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/ive/board/{boardid}/post/{postid}/?reply=2040500",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/ive/board/{boardid}/post/{postid}/?reply=2040500",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_user2artis() -> Never:
    # sample post uuid
    postid: str = "019a27bf-d625-4cf3-0443-dc91b64608e9"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?reply=2007535",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = (f"https://berriz.in/iu/board/{boardid}/post/{postid}/?reply=2007535",)
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def get_results_selected_media() -> selected_media_list:
    """2. Community_Uniqueness List[dict[tuple, str | list[str]]]
    - make a pre list for process
    - key is community_id community_name community_name_nickname
    - valus is class selected_media_list
    - detil in lib\\interface\\interface.py
    """
    results_selected_media: selected_media_list = await Community_Uniqueness.group_by_community()
    return results_selected_media


async def start_run_process(results_selected_media: selected_media_list) -> Never:
    """3. Get results_selected_media this is a Regularization list for next process"""
    if results_selected_media != []:
        await StartProcess(results_selected_media).process()
    await close_session()


async def close_session() -> Never:
    """4. Make sure manuel close session after program end and leave funcation"""
    await BAPIClient.close_session()


if __name__ == "__main__":

    async def main() -> Never:
        """
        1. URL Parser and per all vaild urls data
        each chunk def will return a bool for status
        """
        bool_return: bool = await media_video()
        bool_return: bool = await media_live()
        bool_return: bool = await media_image()
        bool_return: bool = await notice()
        bool_return: bool = await board_post()
        bool_return: bool = await board_post_comment_last()
        bool_return: bool = await board_post_reply_artis()
        bool_return: bool = await board_post_reply_user2user()
        bool_return: bool = await board_post_reply_user2artis()
        """2. after all url parser finsh, collect all data into a class selected_media_list"""
        results_selected_media: selected_media_list = await get_results_selected_media()
        """3. start download process"""
        await start_run_process(results_selected_media)

    asyncio.run(main())
