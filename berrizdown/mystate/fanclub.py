from typing import Any

from lib.__init__ import use_proxy
from lib.lock_cookie import Lock_Cookie, cookie_session
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import My

logger = setup_logging("fanclub", "orange")


class FanClub:
    async def check_cookie(self) -> str | None:
        if cookie_session == {}:
            await Lock_Cookie.cookie_session()

    _fanclub_cache: dict[str, Any] | None = None

    async def request_fanclub(self) -> dict[str, Any]:
        if self._fanclub_cache is None:
            self._fanclub_cache = await My().fetch_fanclub(use_proxy)
            logger.debug(f"Fanclub api response: {self._fanclub_cache}")
        return self._fanclub_cache

    async def fanclub_main(self) -> str | None:
        if cookie_session == {}:
            return "COOKIE_NOT_FOUND"
        data = await self.request_fanclub()
        code: str | None = data.get("code")
        message: str | None = data.get("message")
        fanclub_list: list[dict[str, Any]] | None = data.get("data", {}).get("fanclubs")

        if code == "0000" and fanclub_list and len(fanclub_list) > 0:
            for i in fanclub_list:
                fanclub_info: dict[str, Any] = i.get("fanclubInfo", {})
                subscriber_info: dict[str, Any] = i.get("subscriberInfo", {})

                productKey: str | None = fanclub_info.get("productKey")
                productName: str | None = fanclub_info.get("productName")
                artistName: str | None = fanclub_info.get("artistName")
                generation: str | None = fanclub_info.get("generation")
                cardImageFront: str | None = fanclub_info.get("cardImageFront")
                cardImageBack: str | None = fanclub_info.get("cardImageBack")
                badgeImage: str | None = fanclub_info.get("badgeImage")
                status: str | None = fanclub_info.get("status")
                startDate: str | None = fanclub_info.get("startDate")
                endDate: str | None = fanclub_info.get("endDate")
                verifyStartDate: str | None = fanclub_info.get("verifyStartDate")
                verifyEndDate: str | None = fanclub_info.get("verifyEndDate")
                isVerifiable: bool | None = fanclub_info.get("isVerifiable")

                subscriptionStartDate: str | None = subscriber_info.get("subscriptionStartDate")
                subscriptionEndDate: str | None = subscriber_info.get("subscriptionEndDate")
                purchaseDate: str | None = subscriber_info.get("purchaseDate")
                fanclubUserCode: str | None = subscriber_info.get("fanclubUserCode")
                status: str | None = subscriber_info.get("status")
                return artistName

        return "NOFANCLUBINFO"
