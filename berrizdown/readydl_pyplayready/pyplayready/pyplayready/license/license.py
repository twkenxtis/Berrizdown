from __future__ import annotations

import base64
import copy
import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Iterator

from Crypto.PublicKey import ECC
from pyplayready import Crypto
from pyplayready.license.xmrlicense import XMRLicense
from pyplayready.misc.exceptions import InvalidLicense
from pyplayready.system.bcert import BCertKeyUsage, CertificateChain
from pyplayready.system.util import Util


class License:
    def __init__(self, data: str | bytes | ET.Element):
        if not data:
            raise InvalidLicense("Data must not be empty")

        if isinstance(data, str):
            data = data.encode()

        if isinstance(data, bytes):
            self._root = ET.fromstring(data)
        elif isinstance(data, ET.Element):
            self._root = data
        else:
            raise InvalidLicense("Invalid data type")

        self._original_root = copy.deepcopy(self._root)
        Util.remove_namespaces(self._root)

        if self._root.tag != "AcquireLicenseResponse":
            raise InvalidLicense("License root must be AcquireLicenseResponse")

        self._Response = self._root.find("AcquireLicenseResult/Response")

        if self._Response is None:
            raise InvalidLicense("Response not found in license")

        self.rmsdk_version = self._Response.get("rmsdkVersion")

        self._LicenseResponse = self._Response.find("LicenseResponse")
        if self._Response is None:
            raise InvalidLicense("LicenseResponse not found in license")

        self.version = self._LicenseResponse.findtext("Version")

        self.licenses = list(self._load_licenses())
        self.rev_info = self._LicenseResponse.find("RevInfo")

        self.transaction_id = self._LicenseResponse.find("Acknowledgement/TransactionID")

        self.license_nonce = self._LicenseResponse.findtext("LicenseNonce")
        self.response_id = self._LicenseResponse.findtext("ResponseID")

        cert_chain_str = self._LicenseResponse.findtext("SigningCertificateChain")
        self.signing_certificate_chain = CertificateChain.loads(cert_chain_str) if cert_chain_str else None

    def _find_element_raw(self, name: str) -> ET.Element:
        return self._original_root.find(
            f".//{name}",
            {
                "": "http://www.w3.org/2000/09/xmldsig#",
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "proto": "http://schemas.microsoft.com/DRM/2007/03/protocols",
                "msg": "http://schemas.microsoft.com/DRM/2007/03/protocols/messages",
            },
        )

    def _load_licenses(self) -> Iterator[XMRLicense]:
        Licenses = self._LicenseResponse.findall("Licenses/License")
        if Licenses is None:
            return iter([])

        for license_ in Licenses:
            yield XMRLicense.loads(license_.text)

    def is_verifiable(self):
        if self.signing_certificate_chain is None:
            return False

        signature = self._Response.find("Signature")

        if signature is None:
            return False
        if signature.findtext("SignedInfo/Reference/DigestValue") is None:
            return False
        if signature.findtext("SignatureValue") is None:
            return False

        return True

    def verify(self):
        if not self.is_verifiable():
            raise RuntimeError("Missing required information for license signature verification")

        ET.register_namespace("", "http://schemas.microsoft.com/DRM/2007/03/protocols")

        license_response_xml = ET.tostring(self._find_element_raw("proto:LicenseResponse"), short_empty_elements=False)
        response_hash = hashlib.sha256(license_response_xml).digest()

        Signature = self._Response.find("Signature")
        digest_value = base64.b64decode(Signature.findtext("SignedInfo/Reference/DigestValue"))

        if digest_value != response_hash:
            raise InvalidLicense("Digest mismatch in license")

        signing_leaf_cert = self.signing_certificate_chain.get(0)
        signing_key_bytes = signing_leaf_cert.get_key_by_usage(BCertKeyUsage.SIGN_RESPONSE)

        signing_key = ECC.construct(
            point_x=int.from_bytes(signing_key_bytes[:32], "big"),
            point_y=int.from_bytes(signing_key_bytes[32:], "big"),
            curve="P-256",
        )

        ET.register_namespace("", "http://www.w3.org/2000/09/xmldsig#")
        signed_info_xml = ET.tostring(self._find_element_raw("SignedInfo"), short_empty_elements=False)

        signature_value = base64.b64decode(Signature.findtext("SignatureValue"))

        if not Crypto.ecc256_verify(signing_key, signed_info_xml, signature_value):
            raise InvalidLicense("Signature mismatch in license")

        return True
