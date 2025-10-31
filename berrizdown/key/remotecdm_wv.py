from __future__ import annotations

import base64
import binascii
import re

import aiohttp
import httpx
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import pss
from google.protobuf.message import DecodeError
from lib.load_yaml_config import CFG
from pywidevine.cdm import Cdm
from pywidevine.device import Device, DeviceTypes
from pywidevine.exceptions import (
    DeviceMismatch,
    InvalidInitData,
    InvalidLicenseMessage,
    InvalidLicenseType,
    SignatureMismatch,
)
from pywidevine.key import Key
from pywidevine.license_protocol_pb2 import (
    ClientIdentification,
    License,
    LicenseType,
    SignedDrmCertificate,
    SignedMessage,
)
from pywidevine.pssh import PSSH
from unit.__init__ import USERAGENT
from unit.handle.handle_log import setup_logging

logger = setup_logging("remotecdm_pr", "crimson")


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
        if isinstance(device_type, str):
            device_type = DeviceTypes[device_type]

        for param, name in [
            (device_type, "device_type"),
            (system_id, "system_id"),
            (security_level, "security_level"),
            (host, "host"),
            (secret, "secret"),
            (device_name, "device_name"),
        ]:
            if not param:
                raise ValueError(f"{name} must be provided")

        self.device_type = device_type
        self.system_id = system_id
        self.security_level = security_level
        self.host = host
        self.device_name = device_name

        super().__init__(
            device_type,
            system_id,
            security_level,
            ClientIdentification(),
            RSA.generate(2048),
        )

        self.__session = httpx.Client(http2=True, verify=True, timeout=httpx.Timeout(600.0))
        self.__session.headers.update({"X-Secret-Key": secret})

        r = httpx.head(self.host)
        if r.status_code != 200:
            raise ValueError(f"Could not test Remote API version [{r.status_code}]")

        server = r.headers.get("Server", "")
        if "pywidevine serve" not in server.lower():
            raise ValueError(f"Invalid pywidevine serve API ({server})")

        version_match = re.search(r"pywidevine serve v([\d.]+)", server, re.IGNORECASE)
        if not version_match or version_match.group(1) < "1.4.3":
            raise ValueError("Unsupported pywidevine serve API version")

    @classmethod
    def from_device(cls, device: Device) -> RemoteCdm:
        raise NotImplementedError("Cannot load RemoteCdm from local Device file")

    def open(self) -> bytes:
        r = self.__session.get(f"{self.host}/{self.device_name}/open").json()
        if r["status"] != 200:
            raise ValueError(f"Cannot open session: {r['message']} [{r['status']}]")

        data = r["data"]
        if int(data["device"]["system_id"]) != self.system_id:
            raise DeviceMismatch("System ID mismatch")
        if int(data["device"]["security_level"]) != self.security_level:
            raise DeviceMismatch("Security level mismatch")

        return bytes.fromhex(data["session_id"])

    def close(self, session_id: bytes) -> None:
        r = self.__session.get(f"{self.host}/{self.device_name}/close/{session_id.hex()}").json()
        if r["status"] != 200:
            raise ValueError(f"Cannot close session: {r['message']} [{r['status']}]")

    def set_service_certificate(self, session_id: bytes, certificate: bytes | str | None) -> str:
        cert_b64 = None if certificate is None else (certificate if isinstance(certificate, str) else base64.b64encode(certificate).decode())

        r = self.__session.post(
            f"{self.host}/{self.device_name}/set_service_certificate",
            json={"session_id": session_id.hex(), "certificate": cert_b64},
        ).json()

        if r["status"] != 200:
            raise ValueError(f"Cannot set certificate: {r['message']} [{r['status']}]")
        return r["data"]["provider_id"]

    def get_service_certificate(self, session_id: bytes) -> SignedDrmCertificate | None:
        r = self.__session.post(
            f"{self.host}/{self.device_name}/get_service_certificate",
            json={"session_id": session_id.hex()},
        ).json()

        if r["status"] != 200:
            raise ValueError(f"Cannot get certificate: {r['message']} [{r['status']}]")

        cert_data = r["data"]["service_certificate"]
        if not cert_data:
            return None

        cert_bytes = base64.b64decode(cert_data)
        signed_cert = SignedDrmCertificate()

        try:
            signed_cert.ParseFromString(cert_bytes)
            if signed_cert.SerializeToString() != cert_bytes:
                raise DecodeError("partial parse")
        except DecodeError as e:
            raise DecodeError(f"Invalid SignedDrmCertificate: {e}")

        try:
            pss.new(RSA.import_key(self.root_cert.public_key)).verify(
                msg_hash=SHA1.new(signed_cert.drm_certificate),
                signature=signed_cert.signature,
            )
        except (ValueError, TypeError):
            raise SignatureMismatch("Certificate signature mismatch")

        return signed_cert

    def get_license_challenge(
        self,
        session_id: bytes,
        pssh: PSSH,
        license_type: str = "STREAMING",
        privacy_mode: bool = True,
    ) -> bytes:
        if not isinstance(pssh, PSSH):
            raise InvalidInitData(f"Expected PSSH, got {type(pssh)}")
        if license_type not in LicenseType.keys():
            raise InvalidLicenseType(f"Invalid license_type: {license_type}")

        r = self.__session.post(
            f"{self.host}/{self.device_name}/get_license_challenge/{license_type}",
            json={
                "session_id": session_id.hex(),
                "init_data": pssh.dumps(),
                "privacy_mode": privacy_mode,
            },
        ).json()

        if r["status"] != 200:
            raise ValueError(f"Cannot get challenge: {r['message']} [{r['status']}]")

        challenge = base64.b64decode(r["data"]["challenge_b64"])
        msg = SignedMessage()

        try:
            msg.ParseFromString(challenge)
            if msg.SerializeToString() != challenge:
                raise DecodeError("partial parse")
        except DecodeError as e:
            raise InvalidLicenseMessage(f"Invalid license request: {e}")

        return msg.SerializeToString()

    def parse_license(self, session_id: bytes, license_message: SignedMessage | bytes | str) -> None:
        if not license_message:
            raise InvalidLicenseMessage("Empty license_message")

        if isinstance(license_message, str):
            try:
                license_message = base64.b64decode(license_message)
            except (binascii.Error, binascii.Incomplete) as e:
                raise InvalidLicenseMessage(f"Base64 decode failed: {e}")

        if isinstance(license_message, bytes):
            signed_msg = SignedMessage()
            try:
                signed_msg.ParseFromString(license_message)
                if signed_msg.SerializeToString() != license_message:
                    raise DecodeError("partial parse")
            except DecodeError as e:
                raise InvalidLicenseMessage(f"Invalid SignedMessage: {e}")
            license_message = signed_msg

        if license_message.type != SignedMessage.MessageType.Value("LICENSE"):
            raise InvalidLicenseMessage("Expected LICENSE message type")

        r = self.__session.post(
            f"{self.host}/{self.device_name}/parse_license",
            json={
                "session_id": session_id.hex(),
                "license_message": base64.b64encode(license_message.SerializeToString()).decode(),
            },
        ).json()

        if r["status"] != 200:
            raise ValueError(f"Cannot parse license: {r['message']} [{r['status']}]")

    def get_keys(self, session_id: bytes, type_: int | str | None = None) -> list[Key]:
        if isinstance(type_, str):
            License.KeyContainer.KeyType.Value(type_)
        elif isinstance(type_, int):
            type_ = License.KeyContainer.KeyType.Name(type_)
        elif type_ is None:
            type_ = "ALL"
        else:
            raise TypeError(f"Invalid type_: {type_}")

        r = self.__session.post(
            f"{self.host}/{self.device_name}/get_keys/{type_}",
            json={"session_id": session_id.hex()},
        ).json()

        if r["status"] != 200:
            raise ValueError(f"Cannot get keys: {r['message']} [{r['status']}]")

        return [
            Key(
                type_=k["type"],
                kid=Key.kid_to_uuid(bytes.fromhex(k["key_id"])),
                key=bytes.fromhex(k["key"]),
                permissions=k["permissions"],
            )
            for k in r["data"]["keys"]
        ]


class Remotecdm_Widevine:
    def __init__(self) -> None:
        self.url = "https://berriz.drmkeyserver.com/widevine_license"

    def get_config(self):
        for config in CFG["remote_cdm"]:
            if config["name"] == "widevine":
                return config

    def get_rcdm(self) -> RemoteCdm:
        CF: dict[str, int] = self.get_config()
        if CF["device_type"] is None:
            device_type = DeviceTypes.ANDROID
        elif str(CF["device_type"]) == "DeviceTypes.ANDROID":
            device_type = DeviceTypes.ANDROID
        else:
            device_type = CF["device_type"]

        rcdm = RemoteCdm(
            device_type=device_type,
            system_id=int(CF["system_id"]),
            security_level=int(CF["security_level"]),
            host=str(CF["host"]),
            secret=str(CF["secret"]),
            device_name=str(CF["device_name"]),
        )
        return rcdm

    def get_pssh(self, pssh_input: str) -> PSSH:
        if pssh_input is None or len(pssh_input) != 76:
            raise ValueError("Invalid PSSH")
        else:
            return PSSH(base64.b64decode(pssh_input))

    async def get_license_key(self, pssh_input: str, acquirelicenseassertion: str) -> list[str]:
        rcdm: RemoteCdm = self.get_rcdm()
        session_id = rcdm.open()
        PSSH: PSSH = self.get_pssh(pssh_input)
        challenge = rcdm.get_license_challenge(session_id, PSSH, "STREAMING", True)
        headers = {
            "user-agent": USERAGENT,
            "content-type": "application/octet-stream",
            "acquirelicenseassertion": acquirelicenseassertion,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, data=challenge) as response:
                license_response = await response.read()
        rcdm.parse_license(session_id, license_response)
        key_list: list[str] = []
        for key in rcdm.get_keys(session_id, "CONTENT"):
            key_list.append(f"{key.kid.hex}:{key.key.hex()}")
        rcdm.close(session_id)
        return key_list
