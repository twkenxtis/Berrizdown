import asyncio
from functools import cached_property
from typing import Any

from berrizdown.lib.__init__ import use_proxy
from berrizdown.static.api_error_handle import api_error_handle
from berrizdown.static.color import Color
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import BerrizAPIClient, Community

logger = setup_logging("berriz_create_community", "peacock")


class BerrizCreateCommunity:
    def __init__(self, communityinput1: int | str, communityinput2: int | str) -> None:
        self.communityinput1: int | str = communityinput1
        self.communityinput2: int | str = communityinput2

    @cached_property
    def Community(self) -> Community:
        return Community()

    @cached_property
    def BAPI(self) -> BerrizAPIClient:
        return BerrizAPIClient()

    async def community_id_name(self) -> tuple[int | None, str | None]:
        community_id: int | None = None
        communityname: str | None = None
        if isinstance(self.communityinput1, int):
            community_id = self.communityinput1
            communityname = self.communityinput2
        else:
            community_id = self.communityinput2
            communityname = self.communityinput1
        return community_id, communityname

    def print_data_with_fstring(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            logger.info(f"{Color.fg('violet')}{key}:  {Color.fg('pink')}{value}{Color.reset()}")

    async def community_join(self) -> bool:
        community_id, communityname = await self.community_id_name()
        name: str
        while True:
            logger.info(f"{Color.fg('light_gray')}try join to {Color.fg('aquamarine')}{communityname}{Color.reset()}")
            try:
                name = input(f"{Color.fg('light_yellow')}Please enter name for your {Color.fg('aquamarine')}[{communityname}]{Color.fg('light_yellow')} community's nickname:{Color.reset()} ").strip()
            except EOFError:
                print("")
                await self.BAPI.close_session()
                raise KeyboardInterrupt("User exit program")

            if len(name) > 15:
                logger.warning(f"{name} community name only accept length < 15")
            else:
                break

        data: dict[str, Any] | None = await self.Community.create_community(community_id, name, use_proxy)
        if data is None:
            await self.BAPI.close_session()
            raise KeyboardInterrupt("No return")
        code: str = data.get("code")
        if code == "0000":
            logger.info(f"{Color.fg('light_gray')}Welcome to {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community{Color.reset()}")
            if "data" in data and isinstance(data["data"], dict):
                self.print_data_with_fstring(data["data"])
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")
        elif code != "0000":
            logger.error(f"{api_error_handle(code)}")
            logger.error(f"{Color.fg('steel_blue')}Failed to join the {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community.{Color.reset()}")
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")
        else:
            logger.error(data)
            logger.error(f"{Color.fg('steel_blue')}Failed to join the {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community.{Color.reset()}")
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")

    async def leave_community_main(self) -> bool:
        community_id, communityname = await self.community_id_name()
        userinput: str
        while True:
            logger.info(f"{Color.fg('light_gray')}try leave to {Color.fg('aquamarine')}{communityname}{Color.reset()}")
            print(
                f"{Color.bold()}{Color.fg('plum')}Note:\n{Color.reset()}"
                f"{Color.fg('mint')}Leave this community?\n"
                f"You won’t be able to edit or delete posts and comments made with this profile. "
                f"Even if you rejoin, your previous activity cannot be restored.{Color.reset()}"
            )
            await asyncio.sleep(0.65)
            try:
                userinput = input(f"{Color.fg('gold')}typing YES to accept: {Color.reset()}").strip()
            except EOFError:
                print("")
                await self.BAPI.close_session()
                raise KeyboardInterrupt("User exit program")
            if userinput == "YES":
                break
            elif userinput == "yes":
                logger.warning("Try typing in all caps")

        data: dict[str, Any] | None = await self.Community.leave_community(community_id, use_proxy)
        if data is None:
            await self.BAPI.close_session()
            raise KeyboardInterrupt("No return")
        code: str = data.get("code")
        if code == "0000":
            logger.info(f"{Color.fg('rose')}Successfully left the {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community.{Color.reset()}")
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")
        elif code != "0000":
            logger.error(f"{api_error_handle(code)}")
            logger.error(f"{Color.fg('steel_blue')}Failed to leave the {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community.{Color.reset()}")
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")
        else:
            logger.error(data)
            logger.error(f"{Color.fg('steel_blue')}Failed to leave the {Color.fg('aquamarine')}{communityname} {Color.fg('light_gray')}community.{Color.reset()}")
            await self.BAPI.close_session()
            raise KeyboardInterrupt("exit program")
