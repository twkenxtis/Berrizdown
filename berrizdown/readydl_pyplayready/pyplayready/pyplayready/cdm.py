from __future__ import annotations

import xml.etree.ElementTree as ET
from uuid import UUID

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from ecpy.curves import Curve, Point

from pyplayready.crypto import Crypto
from pyplayready.crypto.ecc_key import ECCKey
from pyplayready.license.key import Key
from pyplayready.license.license import License
from pyplayready.misc.exceptions import (
    InvalidSession,
    InvalidXmrLicense,
    TooManySessions,
)
from pyplayready.misc.revocation_list import RevocationList
from pyplayready.misc.soap_message import SoapMessage
from pyplayready.misc.storage import Storage
from pyplayready.system.bcert import CertificateChain
from pyplayready.system.builder import XmlBuilder
from pyplayready.system.session import Session
from pyplayready.system.wrmheader import WRMHeader


class Cdm:
    MAX_NUM_OF_SESSIONS = 16

    def __init__(
        self,
        security_level: int,
        certificate_chain: CertificateChain | None,
        encryption_key: ECCKey | None,
        signing_key: ECCKey | None,
        client_version: str = "10.0.16384.10011",
    ):
        self.security_level = security_level
        self.certificate_chain = certificate_chain
        self.encryption_key = encryption_key
        self.signing_key = signing_key
        self.client_version = client_version

        self._wmrm_key = Point(
            x=0xC8B6AF16EE941AADAA5389B4AF2C10E356BE42AF175EF3FACE93254E7B0B3D9B,
            y=0x982B27B5CB2341326E56AA857DBFD5C634CE2CF9EA74FCA8F2AF5957EFEEA562,
            curve=Curve.get_curve("secp256r1"),
        )

        self.__sessions: dict[bytes, Session] = {}

    @classmethod
    def from_device(cls, device) -> Cdm:
        """Initialize a Playready CDM from a Playready Device (.prd) file"""
        return cls(
            security_level=device.security_level,
            certificate_chain=device.group_certificate,
            encryption_key=device.encryption_key,
            signing_key=device.signing_key,
        )

    def open(self) -> bytes:
        """Open a Playready Content Decryption Module (CDM) session"""
        if len(self.__sessions) > self.MAX_NUM_OF_SESSIONS:
            raise TooManySessions(f"Too many Sessions open ({self.MAX_NUM_OF_SESSIONS}).")

        session = Session(len(self.__sessions) + 1)
        self.__sessions[session.id] = session

        return session.id

    def close(self, session_id: bytes) -> None:
        """Close a Playready Content Decryption Module (CDM) session"""
        session = self.__sessions.get(session_id)
        if not session:
            raise InvalidSession(f"Session identifier {session_id.hex()} is invalid.")
        del self.__sessions[session_id]

    def _get_cipher_data(self, session: Session) -> bytes:
        body = XmlBuilder.ClientData([self.certificate_chain], ["AESCBCS"])

        cipher = AES.new(key=session.xml_key.aes_key, mode=AES.MODE_CBC, iv=session.xml_key.aes_iv)

        ciphertext = cipher.encrypt(pad(body.encode(), AES.block_size))

        return session.xml_key.aes_iv + ciphertext

    def get_license_challenge(
        self,
        session_id: bytes,
        wrm_header: WRMHeader | str,
        rev_lists: list[UUID] | None = None,  # default: RevocationList.SupportedListIds
    ) -> str:
        session = self.__sessions.get(session_id)
        if not session:
            raise InvalidSession(f"Session identifier {session_id.hex()} is invalid.")

        if isinstance(wrm_header, str):
            wrm_header = WRMHeader(wrm_header)
        if not isinstance(wrm_header, WRMHeader):
            raise ValueError(f"Expected wrm_header to be a {str} or {WRMHeader} not {wrm_header!r}")

        if rev_lists and not isinstance(rev_lists, list):
            raise ValueError(f"Expected rev_lists to be a {list} not {rev_lists!r}")

        match wrm_header.version:
            case WRMHeader.Version.VERSION_4_3_0_0:
                protocol_version = 5
            case WRMHeader.Version.VERSION_4_2_0_0:
                protocol_version = 4
            case _:
                protocol_version = 1

        session.signing_key = self.signing_key
        session.encryption_key = self.encryption_key

        acquire_license_message = XmlBuilder.AcquireLicenseMessage(
            wrmheader=wrm_header.dumps(),
            protocol_version=protocol_version,
            wrmserver_data=Crypto.ecc256_encrypt(self._wmrm_key, session.xml_key.get_point()),
            client_data=self._get_cipher_data(session),
            signing_key=self.signing_key,
            client_info=self.client_version,
            revocation_lists=rev_lists,
        )
        soap_message = SoapMessage.create(acquire_license_message)

        return soap_message.dumps()

    def parse_license(self, session_id: bytes, soap_message: str) -> None:
        session = self.__sessions.get(session_id)
        if not session:
            raise InvalidSession(f"Session identifier {session_id.hex()} is invalid.")

        if not soap_message:
            raise InvalidXmrLicense("Cannot parse an empty licence message")
        if not isinstance(soap_message, str):
            raise InvalidXmrLicense(f"Expected licence message to be a {str}, not {soap_message!r}")
        if not session.encryption_key or not session.signing_key:
            raise InvalidSession("Cannot parse a license message without first making a license request")

        soap_message = SoapMessage.loads(soap_message)
        soap_message.raise_faults()

        licence = License(soap_message.get_message())
        if licence.is_verifiable():
            licence.verify()

        if licence.rev_info is not None:
            current_rev_info_file = Storage.read_file(RevocationList.CurrentRevListStorageName)

            if current_rev_info_file:
                new_rev_info = RevocationList.merge(ET.fromstring(current_rev_info_file), licence.rev_info)
            else:
                new_rev_info = licence.rev_info

            new_rev_info_xml = ET.tostring(new_rev_info, xml_declaration=True, encoding="utf-8")
            Storage.write_file(RevocationList.CurrentRevListStorageName, new_rev_info_xml)
            Storage.write_file(
                RevocationList.loads(new_rev_info).get_storage_file_name(),
                new_rev_info_xml,
            )

        for xmr_license in licence.licenses:
            session.keys.append(xmr_license.get_content_key(session.encryption_key))

    def get_keys(self, session_id: bytes) -> list[Key]:
        session = self.__sessions.get(session_id)
        if not session:
            raise InvalidSession(f"Session identifier {session_id.hex()} is invalid.")

        return session.keys
