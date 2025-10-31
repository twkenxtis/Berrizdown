from __future__ import annotations

import collections.abc

# monkey patch for construct 2.8.8 compatibility
if not hasattr(collections, "Sequence"):
    collections.Sequence = collections.abc.Sequence

import base64
import time
from enum import IntEnum
from pathlib import Path

from construct import (
    Array,
    Bytes,
    Const,
    Container,
    Embedded,
    GreedyRange,
    Int16ub,
    Int32ub,
    ListContainer,
    Struct,
    Switch,
    this,
)
from Crypto.PublicKey import ECC
from pyplayready.crypto import Crypto
from pyplayready.crypto.ecc_key import ECCKey
from pyplayready.misc.exceptions import InvalidCertificate, InvalidCertificateChain
from pyplayready.system.util import Util


class BCertCertType(IntEnum):
    UNKNOWN = 0x00000000
    PC = 0x00000001
    DEVICE = 0x00000002
    DOMAIN = 0x00000003
    ISSUER = 0x00000004
    CRL_SIGNER = 0x00000005
    SERVICE = 0x00000006
    SILVERLIGHT = 0x00000007
    APPLICATION = 0x00000008
    METERING = 0x00000009
    KEYFILESIGNER = 0x0000000A
    SERVER = 0x0000000B
    LICENSESIGNER = 0x0000000C
    SECURETIMESERVER = 0x0000000D
    RPROVMODELAUTH = 0x0000000E


class BCertObjType(IntEnum):
    BASIC = 0x0001
    DOMAIN = 0x0002
    PC = 0x0003
    DEVICE = 0x0004
    FEATURE = 0x0005
    KEY = 0x0006
    MANUFACTURER = 0x0007
    SIGNATURE = 0x0008
    SILVERLIGHT = 0x0009
    METERING = 0x000A
    EXTDATASIGNKEY = 0x000B
    EXTDATACONTAINER = 0x000C
    EXTDATASIGNATURE = 0x000D
    EXTDATA_HWID = 0x000E
    SERVER = 0x000F
    SECURITY_VERSION = 0x0010
    SECURITY_VERSION_2 = 0x0011
    UNKNOWN_OBJECT_ID = 0xFFFD


class BCertFlag(IntEnum):
    EMPTY = 0x00000000
    EXTDATA_PRESENT = 0x00000001


class BCertObjFlag(IntEnum):
    EMPTY = 0x0000
    MUST_UNDERSTAND = 0x0001
    CONTAINER_OBJ = 0x0002


class BCertSignatureType(IntEnum):
    P256 = 0x0001


class BCertKeyType(IntEnum):
    ECC256 = 0x0001


class BCertKeyUsage(IntEnum):
    UNKNOWN = 0x00000000
    SIGN = 0x00000001
    ENCRYPT_KEY = 0x00000002
    SIGN_CRL = 0x00000003
    ISSUER_ALL = 0x00000004
    ISSUER_INDIV = 0x00000005
    ISSUER_DEVICE = 0x00000006
    ISSUER_LINK = 0x00000007
    ISSUER_DOMAIN = 0x00000008
    ISSUER_SILVERLIGHT = 0x00000009
    ISSUER_APPLICATION = 0x0000000A
    ISSUER_CRL = 0x0000000B
    ISSUER_METERING = 0x0000000C
    ISSUER_SIGN_KEYFILE = 0x0000000D
    SIGN_KEYFILE = 0x0000000E
    ISSUER_SERVER = 0x0000000F
    ENCRYPTKEY_SAMPLE_PROTECTION_RC4 = 0x00000010
    RESERVED2 = 0x00000011
    ISSUER_SIGN_LICENSE = 0x00000012
    SIGN_LICENSE = 0x00000013
    SIGN_RESPONSE = 0x00000014
    PRND_ENCRYPT_KEY_DEPRECATED = 0x00000015
    ENCRYPTKEY_SAMPLE_PROTECTION_AES128CTR = 0x00000016
    ISSUER_SECURETIMESERVER = 0x00000017
    ISSUER_RPROVMODELAUTH = 0x00000018


class BCertFeatures(IntEnum):
    TRANSMITTER = 0x00000001
    RECEIVER = 0x00000002
    SHARED_CERTIFICATE = 0x00000003
    SECURE_CLOCK = 0x00000004
    ANTIROLLBACK_CLOCK = 0x00000005
    RESERVED_METERING = 0x00000006
    RESERVED_LICSYNC = 0x00000007
    RESERVED_SYMOPT = 0x00000008
    SUPPORTS_CRLS = 0x00000009
    SERVER_BASIC_EDITION = 0x0000000A
    SERVER_STANDARD_EDITION = 0x0000000B
    SERVER_PREMIUM_EDITION = 0x0000000C
    SUPPORTS_PR3_FEATURES = 0x0000000D
    DEPRECATED_SECURE_STOP = 0x0000000E


class _BCertStructs:
    Header = Struct(
        "flags" / Int16ub,
        "tag" / Int16ub,
        "length" / Int32ub,
    )

    BasicInfo = Struct(
        "cert_id" / Bytes(16),
        "security_level" / Int32ub,
        "flags" / Int32ub,
        "cert_type" / Int32ub,
        "public_key_digest" / Bytes(32),
        "expiration_date" / Int32ub,
        "client_id" / Bytes(16),
    )

    # TODO: untested
    DomainInfo = Struct(
        "service_id" / Bytes(16),
        "account_id" / Bytes(16),
        "revision_timestamp" / Int32ub,
        "domain_url_length" / Int32ub,
        "domain_url" / Bytes((this.domain_url_length + 3) & 0xFFFFFFFC),
    )

    # TODO: untested
    PCInfo = Struct("security_version" / Int32ub)

    DeviceInfo = Struct("max_license" / Int32ub, "max_header" / Int32ub, "max_chain_depth" / Int32ub)

    FeatureInfo = Struct(
        "feature_count" / Int32ub,  # max. 32
        "features" / Array(this.feature_count, Int32ub),
    )

    KeyInfo = Struct(
        "key_count" / Int32ub,
        "cert_keys"
        / Array(
            this.key_count,
            Struct(
                "type" / Int16ub,
                "length" / Int16ub,
                "flags" / Int32ub,
                "key" / Bytes(this.length // 8),
                "usages_count" / Int32ub,
                "usages" / Array(this.usages_count, Int32ub),
            ),
        ),
    )

    ManufacturerInfo = Struct(
        "flags" / Int32ub,
        "manufacturer_name_length" / Int32ub,
        "manufacturer_name" / Bytes((this.manufacturer_name_length + 3) & 0xFFFFFFFC),
        "model_name_length" / Int32ub,
        "model_name" / Bytes((this.model_name_length + 3) & 0xFFFFFFFC),
        "model_number_length" / Int32ub,
        "model_number" / Bytes((this.model_number_length + 3) & 0xFFFFFFFC),
    )

    SignatureInfo = Struct(
        "signature_type" / Int16ub,
        "signature_size" / Int16ub,
        "signature" / Bytes(this.signature_size),
        "signature_key_size" / Int32ub,
        "signature_key" / Bytes(this.signature_key_size // 8),
    )

    # TODO: untested
    SilverlightInfo = Struct("security_version" / Int32ub, "platform_identifier" / Int32ub)

    # TODO: untested
    MeteringInfo = Struct(
        "metering_id" / Bytes(16),
        "metering_url_length" / Int32ub,
        "metering_url" / Bytes((this.metering_url_length + 3) & 0xFFFFFFFC),
    )

    ExtDataSignKeyInfo = Struct(
        "key_type" / Int16ub,
        "key_length" / Int16ub,
        "flags" / Int32ub,
        "key" / Bytes(this.key_length // 8),
    )

    # TODO: untested
    DataRecord = Struct("data_size" / Int32ub, "data" / Bytes(this.data_size))

    ExtDataSignature = Struct(
        "signature_type" / Int16ub,
        "signature_size" / Int16ub,
        "signature" / Bytes(this.signature_size),
    )

    ExtDataHwid = Struct(
        "record_length" / Int32ub,
        "record_data" / Bytes(this.record_length),
        "padding" / Bytes((4 - (this.record_length % 4)) % 4),
    )

    # defined manually, since refactoring everything is not worth it
    ExtDataContainer = Struct(
        "record" / Struct(Embedded(Header), Embedded(ExtDataHwid)),
        "signature" / Struct(Embedded(Header), Embedded(ExtDataSignature)),
    )

    # TODO: untested
    ServerInfo = Struct("warning_days" / Int32ub)

    # TODO: untested
    SecurityVersion = Struct("security_version" / Int32ub, "platform_identifier" / Int32ub)

    Attribute = Struct(
        Embedded(Header),
        "attribute"
        / Switch(
            lambda this_: this_.tag,
            {
                BCertObjType.BASIC: BasicInfo,
                BCertObjType.DOMAIN: DomainInfo,
                BCertObjType.PC: PCInfo,
                BCertObjType.DEVICE: DeviceInfo,
                BCertObjType.FEATURE: FeatureInfo,
                BCertObjType.KEY: KeyInfo,
                BCertObjType.MANUFACTURER: ManufacturerInfo,
                BCertObjType.SIGNATURE: SignatureInfo,
                BCertObjType.SILVERLIGHT: SilverlightInfo,
                BCertObjType.METERING: MeteringInfo,
                BCertObjType.EXTDATASIGNKEY: ExtDataSignKeyInfo,
                BCertObjType.EXTDATACONTAINER: ExtDataContainer,
                # BCertObjType.EXTDATASIGNATURE: ExtDataSignature,
                # BCertObjType.EXTDATA_HWID: ExtDataHwid,
                BCertObjType.SERVER: ServerInfo,
                BCertObjType.SECURITY_VERSION: SecurityVersion,
                BCertObjType.SECURITY_VERSION_2: SecurityVersion,
            },
            default=Bytes(this.length - 8),
        ),
    )

    BCert = Struct(
        "signature" / Const(b"CERT"),
        "version" / Int32ub,
        "total_length" / Int32ub,
        "certificate_length" / Int32ub,
        "attributes" / GreedyRange(Attribute),
    )

    BCertChain = Struct(
        "signature" / Const(b"CHAI"),
        "version" / Int32ub,
        "total_length" / Int32ub,
        "flags" / Int32ub,
        "certificate_count" / Int32ub,
        "certificates" / GreedyRange(BCert),
    )


class Certificate(_BCertStructs):
    """Represents a BCert"""

    def __init__(
        self,
        parsed_bcert: Container,
        bcert_obj: _BCertStructs.BCert = _BCertStructs.BCert,
    ):
        self.parsed = parsed_bcert
        self._BCERT = bcert_obj

    @classmethod
    def new_leaf_cert(
        cls,
        cert_id: bytes,
        security_level: int,
        client_id: bytes,
        signing_key: ECCKey,
        encryption_key: ECCKey,
        group_key: ECCKey,
        parent: CertificateChain,
        expiry: int = 0xFFFFFFFF,
    ) -> Certificate:
        basic_info = Container(
            cert_id=cert_id,
            security_level=security_level,
            flags=BCertFlag.EMPTY,
            cert_type=BCertCertType.DEVICE,
            public_key_digest=signing_key.public_sha256_digest(),
            expiration_date=expiry,
            client_id=client_id,
        )
        basic_info_attribute = Container(
            flags=BCertObjFlag.MUST_UNDERSTAND,
            tag=BCertObjType.BASIC,
            length=len(_BCertStructs.BasicInfo.build(basic_info)) + 8,
            attribute=basic_info,
        )

        device_info = Container(max_license=10240, max_header=15360, max_chain_depth=2)
        device_info_attribute = Container(
            flags=BCertObjFlag.MUST_UNDERSTAND,
            tag=BCertObjType.DEVICE,
            length=len(_BCertStructs.DeviceInfo.build(device_info)) + 8,
            attribute=device_info,
        )

        feature = Container(
            feature_count=3,
            features=ListContainer(
                [
                    BCertFeatures.SECURE_CLOCK,
                    BCertFeatures.SUPPORTS_CRLS,
                    BCertFeatures.SUPPORTS_PR3_FEATURES,
                ]
            ),
        )
        feature_attribute = Container(
            flags=BCertObjFlag.MUST_UNDERSTAND,
            tag=BCertObjType.FEATURE,
            length=len(_BCertStructs.FeatureInfo.build(feature)) + 8,
            attribute=feature,
        )

        signing_key_public_bytes = signing_key.public_bytes()
        cert_key_sign = Container(
            type=BCertKeyType.ECC256,
            length=len(signing_key_public_bytes) * 8,  # bits
            flags=BCertFlag.EMPTY,
            key=signing_key_public_bytes,
            usages_count=1,
            usages=ListContainer([BCertKeyUsage.SIGN]),
        )

        encryption_key_public_bytes = encryption_key.public_bytes()
        cert_key_encrypt = Container(
            type=BCertKeyType.ECC256,
            length=len(encryption_key_public_bytes) * 8,  # bits
            flags=BCertFlag.EMPTY,
            key=encryption_key_public_bytes,
            usages_count=1,
            usages=ListContainer([BCertKeyUsage.ENCRYPT_KEY]),
        )

        key_info = Container(key_count=2, cert_keys=ListContainer([cert_key_sign, cert_key_encrypt]))
        key_info_attribute = Container(
            flags=BCertObjFlag.MUST_UNDERSTAND,
            tag=BCertObjType.KEY,
            length=len(_BCertStructs.KeyInfo.build(key_info)) + 8,
            attribute=key_info,
        )

        manufacturer_info = parent.get(0).get_attribute(BCertObjType.MANUFACTURER)

        new_bcert_container = Container(
            signature=b"CERT",
            version=1,
            total_length=0,  # filled at a later time
            certificate_length=0,  # filled at a later time
            attributes=ListContainer(
                [
                    basic_info_attribute,
                    device_info_attribute,
                    feature_attribute,
                    key_info_attribute,
                    manufacturer_info,
                ]
            ),
        )

        payload = _BCertStructs.BCert.build(new_bcert_container)
        new_bcert_container.certificate_length = len(payload)
        new_bcert_container.total_length = len(payload) + 144  # signature length

        sign_payload = _BCertStructs.BCert.build(new_bcert_container)
        signature = Crypto.ecc256_sign(group_key, sign_payload)

        group_key_public_bytes = group_key.public_bytes()

        signature_info = Container(
            signature_type=BCertSignatureType.P256,
            signature_size=len(signature),
            signature=signature,
            signature_key_size=len(group_key_public_bytes) * 8,  # bits
            signature_key=group_key_public_bytes,
        )
        signature_info_attribute = Container(
            flags=BCertObjFlag.MUST_UNDERSTAND,
            tag=BCertObjType.SIGNATURE,
            length=len(_BCertStructs.SignatureInfo.build(signature_info)) + 8,
            attribute=signature_info,
        )
        new_bcert_container.attributes.append(signature_info_attribute)

        return cls(new_bcert_container)

    @classmethod
    def loads(cls, data: str | bytes) -> Certificate:
        if isinstance(data, str):
            data = base64.b64decode(data)
        if not isinstance(data, bytes):
            raise ValueError(f"Expecting Bytes or Base64 input, got {data!r}")

        cert = _BCertStructs.BCert
        return cls(parsed_bcert=cert.parse(data), bcert_obj=cert)

    def get_attribute(self, type_: int) -> Container | None:
        for attribute in self.parsed.attributes:
            if attribute.tag == type_:
                return attribute

        return None

    def get_security_level(self) -> int | None:
        basic_info = self.get_attribute(BCertObjType.BASIC)
        if basic_info:
            return basic_info.attribute.security_level

        return None

    def get_name(self) -> str | None:
        manufacturer_info_attr = self.get_attribute(BCertObjType.MANUFACTURER)

        if manufacturer_info_attr:
            manufacturer_info = manufacturer_info_attr.attribute

            manufacturer = Util.un_pad(manufacturer_info.manufacturer_name)
            model_name = Util.un_pad(manufacturer_info.model_name)
            model_number = Util.un_pad(manufacturer_info.model_number)

            return f"{manufacturer} {model_name} {model_number}"

        return None

    def get_type(self) -> int | None:
        basic_info = self.get_attribute(BCertObjType.BASIC)
        if basic_info:
            return basic_info.attribute.cert_type

        return None

    def get_expiration_date(self) -> int | None:
        basic_info = self.get_attribute(BCertObjType.BASIC)
        if basic_info:
            return basic_info.attribute.expiration_date

        return None

    def get_issuer_key(self) -> bytes | None:
        signature_object = self.get_attribute(BCertObjType.SIGNATURE)
        if not signature_object:
            return None

        return signature_object.attribute.signature_key

    def get_key_by_usage(self, key_usage: BCertKeyUsage) -> bytes | None:
        key_info_object = self.get_attribute(BCertObjType.KEY)
        if not key_info_object:
            return None

        for key in key_info_object.attribute.cert_keys:
            for usage in key.usages:
                if usage == key_usage:
                    return key.key

        return None

    def contains_public_key(self, public_key: ECCKey | bytes) -> bool:
        if isinstance(public_key, ECCKey):
            public_key = public_key.public_bytes()

        key_info_object = self.get_attribute(BCertObjType.KEY)
        if not key_info_object:
            return False

        for key in key_info_object.attribute.cert_keys:
            if key.key == public_key:
                return True

        return False

    def dumps(self) -> bytes:
        return self._BCERT.build(self.parsed)

    def _verify_extdata_signature(self) -> None:
        sign_key = self.get_attribute(BCertObjType.EXTDATASIGNKEY)
        if not sign_key:
            raise InvalidCertificate("No extdata sign key object found in certificate")

        sign_key_bytes = sign_key.attribute.key

        signing_key = ECC.construct(
            point_x=int.from_bytes(sign_key_bytes[:32], "big"),
            point_y=int.from_bytes(sign_key_bytes[32:], "big"),
            curve="P-256",
        )

        extdata = self.get_attribute(BCertObjType.EXTDATACONTAINER)
        if not extdata:
            raise InvalidCertificate("No extdata container found in certificate")

        signature = extdata.attribute.signature.signature

        sign_data = _BCertStructs.ExtDataContainer.subcons[0].build(extdata.attribute.record)

        if not Crypto.ecc256_verify(public_key=signing_key, data=sign_data, signature=signature):
            raise InvalidCertificate("Signature of certificate extdata is not authentic")

    def verify_signature(self) -> None:
        signature_object = self.get_attribute(BCertObjType.SIGNATURE)
        if not signature_object:
            raise InvalidCertificate("No signature object found in certificate")

        signature_attribute = signature_object.attribute
        raw_signature_key = signature_attribute.signature_key

        signature_key = ECC.construct(
            curve="P-256",
            point_x=int.from_bytes(raw_signature_key[:32], "big"),
            point_y=int.from_bytes(raw_signature_key[32:], "big"),
        )

        sign_payload = self.dumps()[: self.parsed.certificate_length]

        if not Crypto.ecc256_verify(
            public_key=signature_key,
            data=sign_payload,
            signature=signature_attribute.signature,
        ):
            raise InvalidCertificate("Signature of certificate is not authentic")

        basic_info_attribute = self.get_attribute(BCertObjType.BASIC)
        if not basic_info_attribute:
            raise InvalidCertificate("No basic info object found in certificate")

        if basic_info_attribute.attribute.flags & BCertFlag.EXTDATA_PRESENT == BCertFlag.EXTDATA_PRESENT:
            self._verify_extdata_signature()


class CertificateChain(_BCertStructs):
    """Represents a BCertChain"""

    MSPlayReadyRootIssuerPubKey = bytes(
        [
            0x86,
            0x4D,
            0x61,
            0xCF,
            0xF2,
            0x25,
            0x6E,
            0x42,
            0x2C,
            0x56,
            0x8B,
            0x3C,
            0x28,
            0x00,
            0x1C,
            0xFB,
            0x3E,
            0x15,
            0x27,
            0x65,
            0x85,
            0x84,
            0xBA,
            0x05,
            0x21,
            0xB7,
            0x9B,
            0x18,
            0x28,
            0xD9,
            0x36,
            0xDE,
            0x1D,
            0x82,
            0x6A,
            0x8F,
            0xC3,
            0xE6,
            0xE7,
            0xFA,
            0x7A,
            0x90,
            0xD5,
            0xCA,
            0x29,
            0x46,
            0xF1,
            0xF6,
            0x4A,
            0x2E,
            0xFB,
            0x9F,
            0x5D,
            0xCF,
            0xFE,
            0x7E,
            0x43,
            0x4E,
            0xB4,
            0x42,
            0x93,
            0xFA,
            0xC5,
            0xAB,
        ]
    )

    def __init__(
        self,
        parsed_bcert_chain: Container,
        bcert_chain_obj: _BCertStructs.BCertChain = _BCertStructs.BCertChain,
    ):
        self.parsed = parsed_bcert_chain
        self._BCERT_CHAIN = bcert_chain_obj

    @classmethod
    def loads(cls, data: str | bytes) -> CertificateChain:
        if isinstance(data, str):
            data = base64.b64decode(data)
        if not isinstance(data, bytes):
            raise ValueError(f"Expecting Bytes or Base64 input, got {data!r}")

        cert_chain = _BCertStructs.BCertChain
        return cls(parsed_bcert_chain=cert_chain.parse(data), bcert_chain_obj=cert_chain)

    @classmethod
    def load(cls, path: Path | str) -> CertificateChain:
        if not isinstance(path, (Path, str)):
            raise ValueError(f"Expecting Path object or path string, got {path!r}")
        with Path(path).open(mode="rb") as f:
            return cls.loads(f.read())

    def dumps(self) -> bytes:
        return self._BCERT_CHAIN.build(self.parsed)

    def get_security_level(self) -> int:
        return self.get(0).get_security_level()

    def get_name(self) -> str:
        return self.get(0).get_name()

    def verify_chain(self, check_expiry: bool = False, cert_type: BCertCertType | None = None) -> bool:
        # There should be 1-6 certificates in a chain
        if not (1 <= self.count() <= 6):
            raise InvalidCertificateChain("An invalid maximum license chain depth")

        for i in range(self.count()):
            if i == 0 and cert_type:
                if self.get(i).get_type() != cert_type:
                    raise InvalidCertificateChain("Invalid certificate type")

            self.get(i).verify_signature()

            if check_expiry:
                if time.time() >= self.get(i).get_expiration_date():
                    raise InvalidCertificateChain(f"Certificate {i} has expired")

            if i > 0:
                if not self._verify_adjacent_certs(self.get(i - 1), self.get(i)):
                    raise InvalidCertificateChain("Adjacent certificate validation failed")

            if i == (self.count() - 1):
                if self.get(i).get_issuer_key() != self.MSPlayReadyRootIssuerPubKey:
                    raise InvalidCertificateChain("Root certificate issuer missmatch")

        return True

    @staticmethod
    def _verify_adjacent_certs(child_cert: Certificate, parent_cert: Certificate) -> bool:
        if parent_cert.get_type() != BCertCertType.ISSUER:
            return False

        if child_cert.get_security_level() > parent_cert.get_expiration_date():
            return False

        key_info = parent_cert.get_attribute(BCertObjType.KEY)
        if not key_info:
            return False

        issuer_key = child_cert.get_issuer_key()

        issuer_key_match = False
        for key in key_info.attribute.cert_keys:
            if key.key == issuer_key:
                issuer_key_match = True

        if not issuer_key_match:
            return False

        # TODO:
        #  check issuer rights
        #  check issuer features/key usages

        return True

    def append(self, bcert: Certificate) -> None:
        self.parsed.certificate_count += 1
        self.parsed.certificates.append(bcert.parsed)
        self.parsed.total_length += len(bcert.dumps())

    def prepend(self, bcert: Certificate) -> None:
        self.parsed.certificate_count += 1
        self.parsed.certificates.insert(0, bcert.parsed)
        self.parsed.total_length += len(bcert.dumps())

    def remove(self, index: int) -> None:
        if self.count() <= 0:
            raise InvalidCertificateChain("CertificateChain does not contain any Certificates")
        if index >= self.count():
            raise IndexError(f"No Certificate at index {index}, {self.count()} total")

        self.parsed.certificate_count -= 1
        self.parsed.total_length -= len(self.get(index).dumps())
        self.parsed.certificates.pop(index)

    def get(self, index: int) -> Certificate:
        if self.count() <= 0:
            raise InvalidCertificateChain("CertificateChain does not contain any Certificates")
        if index >= self.count():
            raise IndexError(f"No Certificate at index {index}, {self.count()} total")

        return Certificate(self.parsed.certificates[index])

    def count(self) -> int:
        return self.parsed.certificate_count
