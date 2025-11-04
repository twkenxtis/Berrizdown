from __future__ import annotations

import base64
import binascii
import re

import aiohttp
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import pss
from google.protobuf.message import DecodeError

from berrizdown.wvd.pywidevine.cdm import Cdm
from berrizdown.wvd.pywidevine.device import Device, DeviceTypes
from berrizdown.wvd.pywidevine.exceptions import (
    DeviceMismatch,
    InvalidInitData,
    InvalidLicenseMessage,
    InvalidLicenseType,
    SignatureMismatch,
)
from berrizdown.wvd.pywidevine.key import Key
from berrizdown.wvd.pywidevine.license_protocol_pb2 import (
    ClientIdentification,
    License,
    LicenseType,
    SignedDrmCertificate,
    SignedMessage,
)
from berrizdown.wvd.pywidevine.pssh import PSSH
from berrizdown.lib.__init__ import use_proxy
from berrizdown.static.version import __version__
from berrizdown.unit.handle.handle_log import setup_logging
from berrizdown.unit.http.request_berriz_api import TPD_RemoteCDM_Request

logger = setup_logging("widevine.remotecdm", "mint")


class RemoteCdm(Cdm):
    """Remote Accessible CDM using pywidevine's serve schema."""

    def __init__(
        self,
        device_type: DeviceTypes | str,
        system_id: int,
        security_level: int,
        host: str,
        secret: str,
        device_name: str,
    ):
        """Initialize a Widevine Content Decryption Module (CDM)."""
        if not device_type:
            raise ValueError("Device Type must be provided")
        if isinstance(device_type, str):
            device_type = DeviceTypes[device_type]
        if not isinstance(device_type, DeviceTypes):
            raise TypeError(f"Expected device_type to be a {DeviceTypes!r} not {device_type!r}")

        if not system_id:
            raise ValueError("System ID must be provided")
        if not isinstance(system_id, int):
            raise TypeError(f"Expected system_id to be a {int} not {system_id!r}")

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

        self.device_type: DeviceTypes = device_type
        self.system_id: int = system_id
        self.security_level: int = security_level
        self.host: str = host
        self.device_name: str = device_name
        self.secret: str = secret

        # spoof client_id and rsa_key just so we can construct via super call
        super().__init__(
            device_type,
            system_id,
            security_level,
            ClientIdentification(),
            RSA.generate(2048),
        )

    async def test_remote_api(self) -> None:
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=13),
                headers={"user-agent": f"Berrizdown/{__version__} (+https://github.com/twkenxtis/Berrizdown)"},
            ) as session:
            response = await session.head(self.host)
            if response.status != 200:
                logger.warning(f"Could not test Remote API version [{response.status}]")
            if not response.headers or "pywidevine serve" not in str(response.headers):
                logger.warning(f"This Remote CDM API does not seem to be a pywidevine serve API ({response.headers}).")
            server_version_re = re.search(r"pywidevine serve v([\d.]+)", str(response.headers), re.IGNORECASE)
            if not server_version_re:
                raise ValueError("The pywidevine server API is not stating the version correctly, cannot continue.")
            server_version = server_version_re.group(1)
            if server_version < "1.4.3":
                raise ValueError(f"This pywidevine serve API version ({server_version}) is not supported.")

    @classmethod
    def from_device(cls, device: Device) -> RemoteCdm:
        raise NotImplementedError("You cannot load a RemoteCdm from a local Device file.")

    async def open(self) -> bytes:
        await self.test_remote_api()
        self.__session: TPD_RemoteCDM_Request = TPD_RemoteCDM_Request(self.secret)
        r = await self.__session.get(
            f"{self.host}/{self.device_name}/open",
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot Open CDM Session, {r['message']} [{r['status']}]")
        r = r["data"]

        if int(r["device"]["system_id"]) != self.system_id:
            raise DeviceMismatch("The System ID specified does not match the one specified in the API response.")

        if int(r["device"]["security_level"]) != self.security_level:
            raise DeviceMismatch("The Security Level specified does not match the one specified in the API response.")

        return bytes.fromhex(r["session_id"])

    async def close(self, session_id: bytes) -> None:
        r = await self.__session.get(
            f"{self.host}/{self.device_name}/close/{session_id.hex()}",
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot Close CDM Session, {r['message']} [{r['status']}]")

    async def set_service_certificate(self, session_id: bytes, certificate: bytes | str | None) -> str:
        if certificate is None:
            certificate_b64 = None
        elif isinstance(certificate, str):
            certificate_b64 = certificate  # assuming base64
        elif isinstance(certificate, bytes):
            certificate_b64 = base64.b64encode(certificate).decode()
        else:
            raise DecodeError(f"Expecting Certificate to be base64 or bytes, not {certificate!r}")

        r = await self.__session.post(
            f"{self.host}/{self.device_name}/set_service_certificate",
            {"session_id": session_id.hex(), "certificate": certificate_b64},
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot Set CDMs Service Certificate, {r['message']} [{r['status']}]")
        r = r["data"]

        return r["provider_id"]

    async def get_service_certificate(self, session_id: bytes) -> SignedDrmCertificate | None:
        r = await self.__session.post(
            f"{self.host}/{self.device_name}/get_service_certificate",
            {"session_id": session_id.hex()},
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot Get CDMs Service Certificate, {r['message']} [{r['status']}]")
        r = r["data"]

        service_certificate = r["service_certificate"]
        if not service_certificate:
            return None

        service_certificate = base64.b64decode(service_certificate)
        signed_drm_certificate = SignedDrmCertificate()

        try:
            signed_drm_certificate.ParseFromString(service_certificate)
            if signed_drm_certificate.SerializeToString() != service_certificate:
                raise DecodeError("partial parse")
        except DecodeError as e:
            # could be a direct unsigned DrmCertificate, but reject those anyway
            raise DecodeError(f"Could not parse certificate as a SignedDrmCertificate, {e}")

        try:
            pss.new(RSA.import_key(self.root_cert.public_key)).verify(
                msg_hash=SHA1.new(signed_drm_certificate.drm_certificate),
                signature=signed_drm_certificate.signature,
            )
        except (ValueError, TypeError):
            raise SignatureMismatch("Signature Mismatch on SignedDrmCertificate, rejecting certificate")

        return signed_drm_certificate

    async def get_license_challenge(
        self,
        session_id: bytes,
        pssh: PSSH,
        license_type: str = "STREAMING",
        privacy_mode: bool = True,
    ) -> bytes:
        if not pssh:
            raise InvalidInitData("A pssh must be provided.")
        if not isinstance(pssh, PSSH):
            raise InvalidInitData(f"Expected pssh to be a {PSSH}, not {pssh!r}")

        if not isinstance(license_type, str):
            raise InvalidLicenseType(f"Expected license_type to be a {str}, not {license_type!r}")
        if license_type not in LicenseType.keys():
            raise InvalidLicenseType(f"Invalid license_type value of '{license_type}'. Available values: {LicenseType.keys()}")

        r = await self.__session.post(
            f"{self.host}/{self.device_name}/get_license_challenge/{license_type}",
            {
                "session_id": session_id.hex(),
                "init_data": pssh.dumps(),
                "privacy_mode": privacy_mode,
            },
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot get Challenge, {r['message']} [{r['status']}]")
        r = r["data"]

        try:
            challenge = base64.b64decode(r["challenge_b64"])
            license_message = SignedMessage()
            license_message.ParseFromString(challenge)
            if license_message.SerializeToString() != challenge:
                raise DecodeError("partial parse")
        except DecodeError as e:
            raise InvalidLicenseMessage(f"Failed to parse license request, {e}")

        return license_message.SerializeToString()

    async def parse_license(self, session_id: bytes, license_message: SignedMessage | bytes | str) -> None:
        if not license_message:
            raise InvalidLicenseMessage("Cannot parse an empty license_message")

        if isinstance(license_message, str):
            try:
                license_message = base64.b64decode(license_message)
            except (binascii.Error, binascii.Incomplete) as e:
                raise InvalidLicenseMessage(f"Could not decode license_message as Base64, {e}")

        if isinstance(license_message, bytes):
            signed_message = SignedMessage()
            try:
                signed_message.ParseFromString(license_message)
                if signed_message.SerializeToString() != license_message:
                    raise DecodeError("partial parse")
            except DecodeError as e:
                raise InvalidLicenseMessage(f"Could not parse license_message as a SignedMessage, {e}")
            license_message = signed_message

        if not isinstance(license_message, SignedMessage):
            raise InvalidLicenseMessage(f"Expecting license_response to be a SignedMessage, got {license_message!r}")

        if license_message.type != SignedMessage.MessageType.Value("LICENSE"):
            raise InvalidLicenseMessage(f"Expecting a LICENSE message, not a '{SignedMessage.MessageType.Name(license_message.type)}' message.")

        r = await self.__session.post(
            f"{self.host}/{self.device_name}/parse_license",
            {
                "session_id": session_id.hex(),
                "license_message": base64.b64encode(license_message.SerializeToString()).decode(),
            },
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Cannot parse License, {r['message']} [{r['status']}]")

    async def get_keys(self, session_id: bytes, type_: int | str | None = None) -> list[Key]:
        try:
            if isinstance(type_, str):
                License.KeyContainer.KeyType.Value(type_)  # only test
            elif isinstance(type_, int):
                type_ = License.KeyContainer.KeyType.Name(type_)
            elif type_ is None:
                type_ = "ALL"
            else:
                raise TypeError(f"Expected type_ to be a {License.KeyContainer.KeyType} or int, not {type_!r}")
        except ValueError as e:
            raise ValueError(f"Could not parse type_ as a {License.KeyContainer.KeyType}, {e}")

        r = await self.__session.post(
            f"{self.host}/{self.device_name}/get_keys/{type_}",
            {"session_id": session_id.hex()},
            use_proxy,
        )
        if r["status"] != 200:
            raise ValueError(f"Could not get {type_} Keys, {r['message']} [{r['status']}]")
        r = r["data"]

        return [
            Key(
                type_=key["type"],
                kid=Key.kid_to_uuid(bytes.fromhex(key["key_id"])),
                key=bytes.fromhex(key["key"]),
                permissions=key["permissions"],
            )
            for key in r["keys"]
        ]


__all__ = ("RemoteCdm",)
