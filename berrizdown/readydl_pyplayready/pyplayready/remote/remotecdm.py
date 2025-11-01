from __future__ import annotations

import logging
from uuid import UUID

import requests
from lib.__init__ import use_proxy
from readydl_pyplayready.pyplayready import InvalidXmrLicense
from readydl_pyplayready.pyplayready.cdm import Cdm
from readydl_pyplayready.pyplayready.device import Device
from readydl_pyplayready.pyplayready.license.key import Key
from readydl_pyplayready.pyplayready.misc.exceptions import InvalidInitData
from readydl_pyplayready.pyplayready.system.wrmheader import WRMHeader
from unit.http.request_berriz_api import TPD_RemoteCDM_Request


class RemoteCdm(Cdm):
    """Remote Accessible CDM using pyplayready's serve schema."""

    def __init__(self, security_level: int, host: str, secret: str, device_name: str):
        """Initialize a Playready Content Decryption Module (CDM)."""
        if not security_level:
            raise ValueError("Security Level must be provided")
        if not isinstance(security_level, int):
            raise TypeError(f"Expected security_level to be a {int} not {security_level!r}")

        if not host:
            raise ValueError("API Host must be provided")
        if not isinstance(host, str):
            raise TypeError(f"Expected host to be a {str} not {host!r}")

        if not secret:
            raise ValueError("API Secret must be provided")
        if not isinstance(secret, str):
            raise TypeError(f"Expected secret to be a {str} not {secret!r}")

        if not device_name:
            raise ValueError("API Device name must be provided")
        if not isinstance(device_name, str):
            raise TypeError(f"Expected device_name to be a {str} not {device_name!r}")

        self.security_level = security_level
        self.host = host
        self.device_name = device_name

        # spoof certificate_chain and ecc_key just so we can construct via super call
        super().__init__(security_level, None, None, None)

        self._logger = logging.getLogger()

        # self.__session = requests.Session()
        self.__session: TPD_RemoteCDM_Request = TPD_RemoteCDM_Request(secret)
        response = requests.head(self.host)

        if response.status_code != 200:
            self._logger.warning(f"Could not test Remote API version [{response.status_code}]")

        server = response.headers.get("Server")
        if not server or "playready serve" not in server.lower():
            self._logger.warning(f"This Remote CDM API does not seem to be a playready serve API ({server}).")

    @classmethod
    def from_device(cls, device: Device) -> RemoteCdm:
        raise NotImplementedError("You cannot load a RemoteCdm from a local Device file.")

    async def open(self) -> bytes:
        response = await self.__session.get(
            f"{self.host}/{self.device_name}/open",
            use_proxy,
        )
        return bytes.fromhex(response["data"]["session_id"])

    async def close(self, session_id: bytes) -> None:
        await self.__session.get(
            f"{self.host}/{self.device_name}/close/{session_id.hex()}",
            use_proxy,
        )

    async def get_license_challenge(self, session_id: bytes, wrm_header: WRMHeader | str, rev_lists: list[UUID] | None = None) -> str:
        if not wrm_header:
            raise InvalidInitData("A wrm_header must be provided.")
        if isinstance(wrm_header, WRMHeader):
            wrm_header = wrm_header.dumps()
        if not isinstance(wrm_header, str):
            raise ValueError(f"Expected WRMHeader to be a {str} or {WRMHeader} not {wrm_header!r}")
        if rev_lists and not isinstance(rev_lists, list):
            raise ValueError(f"Expected rev_lists to be a {list} not {rev_lists!r}")

        response = await self.__session.post(
            f"{self.host}/{self.device_name}/get_license_challenge",
            {"session_id": session_id.hex(), "init_data": wrm_header, **({"rev_lists": list(map(str, rev_lists))} if rev_lists else {})},
            use_proxy,
        )
        return response["data"]["challenge"]

    async def parse_license(self, session_id: bytes, license_message: str) -> None:
        if not license_message:
            raise InvalidXmrLicense("Cannot parse an empty license_message")

        if not isinstance(license_message, str):
            raise InvalidXmrLicense(f"Expected license_message to be a {str}, not {license_message!r}")

        await self.__session.post(
            f"{self.host}/{self.device_name}/parse_license",
            {"session_id": session_id.hex(), "license_message": license_message},
            use_proxy,
        )

    async def get_keys(self, session_id: bytes) -> list[Key]:
        response = await self.__session.post(
            f"{self.host}/{self.device_name}/get_keys",
            {"session_id": session_id.hex()},
            use_proxy,
        )
        return [
            Key(key_type=key["type"], key_id=Key.kid_to_uuid(bytes.fromhex(key["key_id"])), key=bytes.fromhex(key["key"]), cipher_type=key["cipher_type"], key_length=key["key_length"]) for key in response["data"]["keys"]
        ]
