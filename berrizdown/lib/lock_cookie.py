import asyncio

from cookies.cookies import Berriz_cookie


class Lock_Cookie:
    """一個用於異步獲取並鎖定 Cookie 會話的類別"""

    @staticmethod
    async def cookie_session(clear=False) -> dict[str, str]:
        """異步獲取 Berriz 的 cookies"""
        if clear is False:
            ck = await Berriz_cookie().get_cookies()
            if ck != {}:
                return ck
            else:
                return {}
        return {}


cookie_session: dict[str, str] = asyncio.run(Lock_Cookie.cookie_session())
