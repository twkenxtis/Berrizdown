import asyncio

from cookies.cookies import Berriz_cookie


class Lock_Cookie:
    """一個用於異步獲取並鎖定 Cookie 會話的類別"""

    @staticmethod
    async def cookie_session(clear=False) -> dict[str, str]:
        """異步獲取 Berriz 的 cookies"""
        o: int = 0
        while True:
            if clear is False:
                o += 1
                ck = await Berriz_cookie().get_cookies()
                if ck != {} or o > 6:
                    return ck
            else:
                return {}


cookie_session: dict[str, str] = asyncio.run(Lock_Cookie.cookie_session())
