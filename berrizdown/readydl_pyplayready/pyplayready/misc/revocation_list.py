from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Union, Optional, Iterator
from uuid import UUID

from Crypto.PublicKey import ECC
from construct import Struct, Bytes, Switch, Int64ul, Int64ub, Int32ub, \
    Int16ub, Int8ub, Array, this, Adapter, OneOf, If, Container, Select, GreedyBytes, String
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from ecpy import curve_defs
from ecpy.curve_defs import WEIERSTRASS
from ecpy.curves import Curve, Point
from ecpy.ecdsa import ECDSA
from ecpy.keys import ECPublicKey
import xml.etree.ElementTree as ET

from readydl_pyplayready.pyplayready import Crypto
from readydl_pyplayready.pyplayready.misc.exceptions import InvalidRevocationList
from readydl_pyplayready.pyplayready.system.bcert import CertificateChain, BCertCertType, BCertKeyUsage
from readydl_pyplayready.pyplayready.system.util import Util


class FileTime(Adapter):
    EPOCH_AS_FILETIME = 116444736000000000
    HUNDREDS_OF_NANOSECONDS = 10_000_000

    def _decode(self, obj, context):
        timestamp = (obj - self.EPOCH_AS_FILETIME) / self.HUNDREDS_OF_NANOSECONDS
        return datetime.fromtimestamp(timestamp, timezone.utc)

    def _encode(self, obj, context):
        return self.EPOCH_AS_FILETIME + int(obj.timestamp() * self.HUNDREDS_OF_NANOSECONDS)


class UUIDLe(Adapter):
    def _decode(self, obj, context):
        return UUID(bytes_le=obj)

    def _encode(self, obj, context):
        return obj.bytes_le


class _RevocationStructs:
    BRevInfoData = Struct(
        "magic" / OneOf(Int32ub, [0x524C5649, 0x524C5632]),  # RLVI / RLV2
        "length" / Int32ub,
        "format_version" / Int8ub,
        "reserved" / Bytes(3),
        "sequence_number" / Int32ub,  # what's this?
        "issued_time" / Switch(lambda ctx: ctx.magic, {
            0x524C5649: FileTime(Int64ul),
            0x524C5632: FileTime(Int64ub),
        }),
        "record_count" / Int32ub,
        "records" / Array(this.record_count, Struct(
            "list_id" / UUIDLe(Bytes(16)),
            "version" / Int64ub
        ))
    )

    BRevInfoSigned = Struct(
        "data" / BRevInfoData,
        "signature_type" / Int8ub,
        "signature_size" / Switch(lambda ctx: ctx.signature_type, {
            1: 128,
            2: Int16ub
        }),
        "signature" / Bytes(this.signature_size),
        "certificate_chain_length" / If(this.signature_type == 1, Int32ub),
        "certificate_chain" / Select(CertificateChain.BCertChain, GreedyBytes)
    )

    BPrRLData = Struct(
        "id" / Bytes(16),
        "version" / Int32ub,
        "entry_count" / Int32ub,
        "revocation_entries" / Array(this.entry_count, Bytes(32)),
    )

    BPrRLSigned = Struct(
        "data" / BPrRLData,
        "signature_type" / Int8ub,
        "signature_length" / Int16ub,
        "signature" / Bytes(this.signature_length),
        "certificate_chain" / Select(CertificateChain.BCertChain, GreedyBytes)
    )

    WMDRMNETData = Struct(
        "version" / Int32ub,
        "entry_count" / Int32ub,
        "revocation_entries" / Array(this.entry_count, Bytes(20)),
        "certificate_chain_length" / Int32ub,
        "certificate_chain" / String(this.certificate_chain_length),
    )

    WMDRMNETSigned = Struct(
        "data" / WMDRMNETData,
        "signature_type" / Int8ub,
        "signature_length" / Int16ub,
        "signature" / Bytes(this.signature_length)
    )


class RevocationList(_RevocationStructs):

    class ListID:
        # Rev Info
        REV_INFO = UUID("CCDE5A55-A688-4405-A88B-D13F90D5BA3E")  # VVrezIimBUSoi9E/kNW6Pg==
        REV_INFO_V2 = UUID("52D1FF11-D388-4EDD-82B7-68EA4C20A16C")  # Ef/RUojT3U6Ct2jqTCChbA==

        # PlayReady Revocation List
        PLAYREADY_RUNTIME = UUID("4E9D8C8A-B652-45A7-9791-6925A6B4791F")  # ioydTlK2p0WXkWklprR5Hw==
        PLAYREADY_APPLICATION = UUID("28082E80-C7A3-40B1-8256-19E5B6D89B27")  # gC4IKKPHsUCCVhnlttibJw==

        # WMDRMNET Revocation List (deprecated: "LegacyXMLCert")
        WMDRMNET = UUID("CD75E604-543D-4A9C-9F09-FE6D24E8BF90")  # BOZ1zT1UnEqfCf5tJOi/kA==

        # WMDRM Device Revocation List
        DEVICE_REVOCATION = UUID("3129E375-CEB0-47D5-9CCA-9DB74CFD4332")  # deMpMbDO1Uecyp23TP1DMg==

        # App Revocation List
        APP_REVOCATION = UUID("90A37313-0ECF-4CAA-A906-B188F6129300")  # E3OjkM8OqkypBrGI9hKTAA==

    SupportedListIds = [ListID.PLAYREADY_RUNTIME, ListID.PLAYREADY_APPLICATION, ListID.REV_INFO_V2, ListID.WMDRMNET]

    RevocationDataPubKeyAllowList = [
        bytes([
            0x3F, 0x3C, 0x09, 0x41, 0xB3, 0xE2, 0x45, 0xC4, 0xF0, 0x55, 0x32, 0xF1, 0x00, 0x40, 0xAA, 0x48,
            0xFD, 0x2A, 0xC8, 0x44, 0x23, 0x68, 0x2D, 0xBF, 0x45, 0xFE, 0x2A, 0x65, 0xFF, 0x4E, 0xFF, 0x3A,
            0x60, 0xC4, 0x2A, 0x71, 0x38, 0x61, 0xA3, 0xA7, 0xBC, 0x89, 0xB3, 0xE7, 0xB9, 0xA4, 0xF4, 0xAA,
            0xA2, 0x8B, 0xA8, 0xCE, 0xE6, 0x89, 0xBA, 0x8D, 0xF7, 0xB0, 0x1B, 0x6A, 0x79, 0xC7, 0xDC, 0x93,
        ])
    ]

    pubkeyWMDRMNDRevocation = bytes([
        0x17, 0xab, 0x8d, 0x43, 0xe6, 0x47, 0xef, 0xba, 0xbd, 0x23,
        0x44, 0x66, 0x9f, 0x64, 0x04, 0x84, 0xf8, 0xe7, 0x71, 0x39,
        0xc7, 0x07, 0x36, 0x25, 0x5d, 0xa6, 0x5f, 0xba, 0xb9, 0x00,
        0xef, 0x9c, 0x89, 0x6b, 0xf2, 0xc4, 0x81, 0x1d, 0xa2, 0x12
    ])

    CurrentRevListStorageName = "RevInfo_Current.xml"

    def __init__(self, parsed):  # List[Tuple[UUID, Container]]
        self.parsed = parsed

    @staticmethod
    def _verify_crl_signatures(crl: Container, data_struct) -> None:
        if isinstance(crl.certificate_chain, bytes) and len(crl.certificate_chain) == 64:
            # TODO: untested, since RLVI is deprecated
            if crl.certificate_chain not in RevocationList.RevocationDataPubKeyAllowList:
                raise InvalidRevocationList("Unallowed revocation list signing public key")

            signing_pub_key = crl.certificate_chain
        else:
            signing_cert = CertificateChain(crl.certificate_chain)
            signing_cert.verify_chain(
                check_expiry=True,
                cert_type=BCertCertType.CRL_SIGNER
            )

            leaf_signing_cert = signing_cert.get(0)
            signing_pub_key = leaf_signing_cert.get_key_by_usage(BCertKeyUsage.SIGN_CRL)

        signing_key = ECC.construct(
            curve='P-256',
            point_x=int.from_bytes(signing_pub_key[:32]),
            point_y=int.from_bytes(signing_pub_key[32:])
        )

        sign_payload = data_struct.build(crl.data)

        if not Crypto.ecc256_verify(
            public_key=signing_key,
            data=sign_payload,
            signature=crl.signature
        ):
            raise InvalidRevocationList("Revocation List signature is not authentic")

    @staticmethod
    def _verify_wmdrmnet_wrap_signature(xml: str) -> bool:
        self = RevocationList

        # Microsoft's ECC1 curve
        msdrm_ecc1_params = {
            'name':       "msdrm-ecc1",
            'type':       WEIERSTRASS,
            'size':       160,
            'field':      0x89abcdef012345672718281831415926141424f7,  # q
            'generator': (0x8723947fd6a3a1e53510c07dba38daf0109fa120,  # gen x
                          0x445744911075522d8c3c5856d4ed7acda379936f), # gen y
            'order':      0x89abcdef012345672716b26eec14904428c2a675,  # n
            'cofactor':   0x1,
            'a':          0x37a5abccd277bce87632ff3d4780c009ebe41497,  # a
            'b':          0x0dd8dabf725e2f3228e85f1ad78fdedf9328239e,  # b
        }

        curve_defs.curves.append(msdrm_ecc1_params)
        msdrm_ecc1 = Curve.get_curve("msdrm-ecc1")

        public_point = Point(
            x=int.from_bytes(self.pubkeyWMDRMNDRevocation[:20], "little"),
            y=int.from_bytes(self.pubkeyWMDRMNDRevocation[20:], "little"),
            curve=msdrm_ecc1,
            check=True
        )

        public_key = ECPublicKey(public_point)

        root = ET.fromstring(f"<root>{xml}</root>")
        signature_value_element = root.find("SIGNATURE/VALUE")

        if signature_value_element is None:
            raise InvalidRevocationList("No SIGNATURE VALUE found in WMDRMNET revocation wrap")

        signature_value = base64.b64decode(signature_value_element.text)
        if len(signature_value) != 40:
            raise InvalidRevocationList("Invalid WMDRMNET revocation wrap SIGNATURE length")

        r = int.from_bytes(signature_value[:20], "little")
        s = int.from_bytes(signature_value[20:], "little")

        if not r < msdrm_ecc1_params["order"] or not s < msdrm_ecc1_params["order"]:
            raise InvalidRevocationList("Invalid WMDRMNET revocation wrap SIGNATURE")

        data_element = root.find("DATA")
        if data_element is None:
            raise InvalidRevocationList("No DATA element found in WMDRMNET revocation wrap")

        # <VALUE> contents = ["<DATA>" | <DATA> element contents | "</DATA>"]
        data_bytes = ET.tostring(data_element, encoding="utf-8")
        data_digest = hashlib.sha1(data_bytes).digest()

        signer = ECDSA("ITUPLE")
        authentic = signer.verify(
            data_digest,
            (r, s),
            public_key
        )

        # Windows Media DRM (WMDRM) Signature verification:
        # Signature values (r, s) and the public key are both little-endian and loaded directly as
        # integers. (We're also not using Montgomery but that shouldn't change anything)
        # Despite loading them correctly and all checks on the pubkey and (r, s) being valid,
        # signature verification still fails and (TODO) I DON'T KNOW WHY
        # Useful sources:
        # http://bearcave.com/misl/misl_tech/msdrm/technical.html
        # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-drmcd/36aabf50-a6be-4eb2-8f36-e1879eb54585
        # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-drm/76e5839c-5395-447a-a48c-3ab724c972a3

        return True

    @staticmethod
    def _unwrap_wmdrmnet_list(xml: str) -> bytes:
        root = ET.fromstring(f"<root>{xml}</root>")
        data_template = root.findtext("DATA/TEMPLATE")

        if not data_template:
            raise InvalidRevocationList("No DATA/TEMPLATE found in WMDRMNET revocation wrap")

        return base64.b64decode(data_template)

    @staticmethod
    def _verify_prnd_certificate(data: str) -> None:
        root = ET.fromstring(data)

        ET.register_namespace("c", "http://schemas.microsoft.com/DRM/2004/02/cert")
        ET.register_namespace("", "http://www.w3.org/2000/09/xmldsig#")

        _ns = {"c": "http://schemas.microsoft.com/DRM/2004/02/cert"}

        for cert in root.findall("c:Certificate", _ns):
            data_elem = cert.find("c:Data", _ns)
            if data_elem is None:
                raise InvalidRevocationList("Missing Data")

            data_xml = ET.tostring(data_elem)

            Util.remove_namespaces(cert)

            digest_val = cert.findtext("Signature/SignedInfo/Reference/DigestValue")
            if not digest_val:
                raise InvalidRevocationList("Missing DigestValue")

            digest_calc = base64.b64encode(hashlib.sha1(data_xml).digest()).decode()
            if digest_val != digest_calc:
                raise InvalidRevocationList("Digest mismatch")

            rsa_key_value = cert.find("Signature/KeyInfo/KeyValue/RSAKeyValue")
            mod_b64 = rsa_key_value.findtext("Modulus")
            exp_b64 = rsa_key_value.findtext("Exponent")
            if not mod_b64 or not exp_b64:
                raise InvalidRevocationList("Missing Modulus/Exponent")

            modulus_int = int.from_bytes(base64.b64decode(mod_b64), "big")

            exp_raw = bytearray(base64.b64decode(exp_b64))
            exp_bytes = (b"\x00" + exp_raw[::-1])
            exponent_int = int.from_bytes(exp_bytes, "big")

            pub_key = rsa.RSAPublicNumbers(exponent_int, modulus_int).public_key(default_backend())

            sig_b64 = cert.findtext("Signature/SignatureValue")
            if not sig_b64:
                raise InvalidRevocationList("Missing SignatureValue")

            sig_bytes = base64.b64decode(sig_b64)

            pub_key.verify(
                signature=sig_bytes,
                data=data_xml,
                padding=padding.PSS(padding.MGF1(hashes.SHA1()), padding.PSS.MAX_LENGTH),
                algorithm=hashes.SHA1()
            )

    @staticmethod
    def _get_wmdrmnet_crl_keys(data: str) -> Iterator[rsa.RSAPublicKey]:
        root = ET.fromstring(data.encode())
        Util.remove_namespaces(root)

        for cert in root.findall('Certificate'):
            data_elem = cert.find("Data")
            if data_elem is None:
                continue

            key_usage_elem = data_elem.findtext('KeyUsage/SignCRL')
            if key_usage_elem != "1":
                continue

            rsa_elem = data_elem.find('PublicKey/KeyValue/RSAKeyValue')
            if rsa_elem is None:
                continue

            modulus_b64 = rsa_elem.findtext('Modulus')
            exponent_b64 = rsa_elem.findtext('Exponent')
            if not modulus_b64 or not exponent_b64:
                continue

            modulus = int.from_bytes(base64.b64decode(modulus_b64), 'big')
            exponent = int.from_bytes(base64.b64decode(exponent_b64), 'big')

            yield rsa.RSAPublicNumbers(exponent, modulus).public_key()

        return None

    @staticmethod
    def _parse_list(list_id: UUID, data: bytes):
        self = RevocationList

        if list_id in (self.ListID.REV_INFO, self.ListID.REV_INFO_V2):
            rev_info = self.BRevInfoSigned.parse(data)
            self._verify_crl_signatures(rev_info, self.BRevInfoData)

            return list_id, rev_info
        elif list_id in (self.ListID.PLAYREADY_RUNTIME, self.ListID.PLAYREADY_APPLICATION):
            pr_rl = self.BPrRLSigned.parse(data)
            self._verify_crl_signatures(pr_rl, self.BPrRLData)

            return list_id, pr_rl
        elif list_id == self.ListID.WMDRMNET:
            try:
                xml = data.decode("utf-16-le")
                if "<DATA>" in xml:
                    if not self._verify_wmdrmnet_wrap_signature(xml):
                        raise InvalidRevocationList("WMDRMNET wrap signature is not authentic")

                    wmdrmnet_data = self._unwrap_wmdrmnet_list(xml)
                else:
                    raise InvalidRevocationList("WMDRMNET revocation list cannot be valid UTF-16-LE and not be wrapped")
            except UnicodeDecodeError:
                wmdrmnet_data = base64.b64decode(data)

            wmdrmnet_parsed = self.WMDRMNETSigned.parse(wmdrmnet_data)
            certificate_chain = wmdrmnet_parsed.data.certificate_chain.decode()

            self._verify_prnd_certificate(certificate_chain)
            crl_pub_key = next(self._get_wmdrmnet_crl_keys(certificate_chain), None)

            crl_pub_key.verify(
                signature=wmdrmnet_parsed.signature,
                data=self.WMDRMNETData.build(wmdrmnet_parsed.data),
                padding=padding.PSS(padding.MGF1(hashes.SHA1()), padding.PSS.MAX_LENGTH),
                algorithm=hashes.SHA1()
            )

            return list_id, wmdrmnet_parsed

        # TODO: DEVICE_REVOCATION, APP_REVOCATION

        return None

    @staticmethod
    def _remove_utf8_bom(data: bytes) -> bytes:
        # https://en.wikipedia.org/wiki/Byte_order_mark#UTF-8

        if data[:3] == b"\xEF\xBB\xBF":
            return data[3:]
        return data

    @staticmethod
    def _verify_and_parse(revocation):
        list_id = revocation.find("ListID")

        if list_id is None or not list_id.text:
            raise InvalidRevocationList(f"<ListID> is either missing or empty")

        list_id_uuid = UUID(bytes_le=base64.b64decode(list_id.text))

        list_data = revocation.find("ListData")
        if list_data is None or not list_data.text:
            raise InvalidRevocationList(f"<ListData> is either missing or empty")

        return RevocationList._parse_list(list_id_uuid, base64.b64decode(list_data.text))

    @classmethod
    def loads(cls, data: Union[str, bytes, ET.Element]) -> RevocationList:
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, bytes):
            root = ET.fromstring(cls._remove_utf8_bom(data))
        else:
            root = data

        if root.tag != "RevInfo":
            raise InvalidRevocationList("Root element is not <RevInfo>")

        revocations = root.findall("Revocation")

        return cls(list(map(
            cls._verify_and_parse,
            revocations
        )))

    @classmethod
    def load(cls, path: Union[Path, str]) -> RevocationList:
        if not isinstance(path, (Path, str)):
            raise ValueError(f"Expecting Path object or path string, got {path!r}")
        with Path(path).open(mode="rb") as f:
            return cls.loads(f.read())

    @staticmethod
    def merge(root: ET.Element, root2: ET.Element) -> ET.Element:
        if root.tag != "RevInfo" or root2.tag != "RevInfo":
            raise InvalidRevocationList("Root element is not <RevInfo>")

        revocation = root.findall("Revocation")

        def _get_version(parsed):
            if parsed[0] in (RevocationList.ListID.REV_INFO, RevocationList.ListID.REV_INFO_V2):
                return parsed[1].data.sequence_number
            return parsed[1].data.version

        def find_in_revs(list_id: UUID):
            for rev in revocation:
                parsed_rev = RevocationList._verify_and_parse(rev)
                if parsed_rev[0] == list_id:
                    return rev, _get_version(parsed_rev)
            return None, None

        for revocation2 in root2.findall("Revocation"):
            parsed_rev2 = RevocationList._verify_and_parse(revocation2)

            rev_find, version = find_in_revs(parsed_rev2[0])
            if rev_find is None:
                root.append(revocation2)
            else:
                if _get_version(parsed_rev2) > version:
                    rev_find.find("ListData").text = revocation2.find("ListData").text

        return root

    def get_by_id(self, uuid: UUID) -> Optional[Container]:
        for rev_list in self.parsed:
            if rev_list[0] == uuid:
                return rev_list[1]

        return None

    def get_storage_file_name(self):
        rev_list = self.get_by_id(self.ListID.REV_INFO_V2)
        list_name = "RevInfo2"

        if rev_list is None:
            rev_list = self.get_by_id(self.ListID.REV_INFO)
            list_name = "RevInfo"

        if rev_list is None:
            raise InvalidRevocationList("No RevInfo available")

        list_version = rev_list.data.sequence_number
        list_date = rev_list.data.issued_time.strftime("%Y%m%d")

        return f"{list_name}v{list_version}_{list_date}.xml"
