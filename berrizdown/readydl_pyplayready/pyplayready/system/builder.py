import base64
import hashlib
import html
import time
import xml.etree.ElementTree as ET
from typing import Optional, List
from uuid import UUID

from Crypto.Random import get_random_bytes

from readydl_pyplayready.pyplayready import ECCKey, Crypto
from readydl_pyplayready.pyplayready.misc.revocation_list import RevocationList
from readydl_pyplayready.pyplayready.misc.storage import Storage
from readydl_pyplayready.pyplayready.system.bcert import CertificateChain


class XmlBuilder:

    @staticmethod
    def _ClientInfo(parent: ET.Element, client_version: str) -> ET.Element:
        ClientInfo = ET.SubElement(parent, "CLIENTINFO")

        ClientVersion = ET.SubElement(ClientInfo, "CLIENTVERSION")
        ClientVersion.text = client_version

        return ClientVersion

    @staticmethod
    def _RevListInfo(parent: ET.Element, list_id: UUID, version: int) -> ET.Element:
        RevListInfo = ET.SubElement(parent, "RevListInfo")

        ListID = ET.SubElement(RevListInfo, "ListID")
        ListID.text = base64.b64encode(list_id.bytes_le).decode()

        Version = ET.SubElement(RevListInfo, "Version")
        Version.text = str(version)

        return RevListInfo

    @staticmethod
    def _RevocationLists(parent: ET.Element, rev_lists: List[UUID]) -> ET.Element:
        RevocationLists = ET.SubElement(parent, "RevocationLists")

        load_result = Storage.read_file(RevocationList.CurrentRevListStorageName)
        if load_result is None:
            for rev_list in rev_lists:
                XmlBuilder._RevListInfo(RevocationLists, rev_list, 0)

            return RevocationLists

        loaded_list = RevocationList.loads(load_result)

        for list_id, list_data in loaded_list.parsed:
            if list_id not in rev_lists:
                continue

            if list_id == RevocationList.ListID.REV_INFO_V2:
                version = list_data.data.sequence_number
            else:
                version = list_data.data.version

            XmlBuilder._RevListInfo(RevocationLists, list_id, version)

        return RevocationLists

    @staticmethod
    def _LicenseAcquisition(
            parent: ET.Element,
            wrmheader: str,
            protocol_version: int,
            wrmserver_data: bytes,
            client_data: bytes,
            client_info: Optional[str] = None,
            revocation_lists: Optional[List[UUID]] = None
    ) -> ET.Element:
        LA = ET.SubElement(parent, "LA", {
            "xmlns": "http://schemas.microsoft.com/DRM/2007/03/protocols",
            "Id": "SignedData",
            "xml:space": "preserve"
        })

        Version = ET.SubElement(LA, "Version")
        Version.text = str(protocol_version)

        ContentHeader = ET.SubElement(LA, "ContentHeader")
        ContentHeader.text = wrmheader

        if client_info is not None:
            XmlBuilder._ClientInfo(LA, client_info)

        if revocation_lists is not None:
            XmlBuilder._RevocationLists(LA, revocation_lists)

        LicenseNonce = ET.SubElement(LA, "LicenseNonce")
        LicenseNonce.text = base64.b64encode(get_random_bytes(16)).decode()

        ClientTime = ET.SubElement(LA, "ClientTime")
        ClientTime.text = str(int(time.time()))

        EncryptedData = ET.SubElement(LA, "EncryptedData", {
            "xmlns": "http://www.w3.org/2001/04/xmlenc#",
            "Type": "http://www.w3.org/2001/04/xmlenc#Element"
        })
        ET.SubElement(EncryptedData, "EncryptionMethod", {
            "Algorithm": "http://www.w3.org/2001/04/xmlenc#aes128-cbc"
        })

        KeyInfo = ET.SubElement(EncryptedData, "KeyInfo", {
            "xmlns": "http://www.w3.org/2000/09/xmldsig#"
        })

        EncryptedKey = ET.SubElement(KeyInfo, "EncryptedKey", {
            "xmlns": "http://www.w3.org/2001/04/xmlenc#"
        })
        ET.SubElement(EncryptedKey, "EncryptionMethod", {
            "Algorithm": "http://schemas.microsoft.com/DRM/2007/03/protocols#ecc256"
        })

        KeyInfoInner = ET.SubElement(EncryptedKey, "KeyInfo", {
            "xmlns": "http://www.w3.org/2000/09/xmldsig#"
        })
        KeyName = ET.SubElement(KeyInfoInner, "KeyName")
        KeyName.text = "WMRMServer"

        WRMServerData = ET.SubElement(ET.SubElement(EncryptedKey, "CipherData"), "CipherValue")
        WRMServerData.text = base64.b64encode(wrmserver_data).decode()

        ClientData = ET.SubElement(ET.SubElement(EncryptedData, "CipherData"), "CipherValue")
        ClientData.text = base64.b64encode(client_data).decode()

        return LA

    @staticmethod
    def _SignedInfo(parent: ET.Element, digest_value: bytes) -> ET.Element:
        SignedInfo = ET.SubElement(parent, "SignedInfo", {
            "xmlns": "http://www.w3.org/2000/09/xmldsig#"
        })
        ET.SubElement(SignedInfo, "CanonicalizationMethod", {
            "Algorithm": "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        })
        ET.SubElement(SignedInfo, "SignatureMethod", {
            "Algorithm": "http://schemas.microsoft.com/DRM/2007/03/protocols#ecdsa-sha256"
        })

        Reference = ET.SubElement(SignedInfo, "Reference", {
            "URI": "#SignedData"
        })
        ET.SubElement(Reference, "DigestMethod", {
            "Algorithm": "http://schemas.microsoft.com/DRM/2007/03/protocols#sha256"
        })
        DigestValue = ET.SubElement(Reference, "DigestValue")
        DigestValue.text = base64.b64encode(digest_value).decode()

        return SignedInfo

    @staticmethod
    def AcquireLicenseMessage(
            wrmheader: str,
            protocol_version: int,
            wrmserver_data: bytes,
            client_data: bytes,
            signing_key: ECCKey,
            client_info: Optional[str] = None,
            revocation_lists: Optional[List[UUID]] = None
    ) -> ET.Element:
        AcquireLicense = ET.Element("AcquireLicense", {
            "xmlns": "http://schemas.microsoft.com/DRM/2007/03/protocols"
        })

        Challenge = ET.SubElement(ET.SubElement(AcquireLicense, "challenge"), "Challenge", {
            "xmlns": "http://schemas.microsoft.com/DRM/2007/03/protocols/messages"
        })

        LA = XmlBuilder._LicenseAcquisition(Challenge, wrmheader, protocol_version, wrmserver_data, client_data, client_info, revocation_lists)

        Signature = ET.SubElement(Challenge, "Signature", {
            "xmlns": "http://www.w3.org/2000/09/xmldsig#"
        })

        la_xml = ET.tostring(
            LA,
            encoding="utf-8",
            short_empty_elements=False
        )
        # I don't like this but re-serializing the WRMHEADER XML could change it
        unescaped_la_xml = html.unescape(la_xml.decode())
        la_digest = hashlib.sha256(unescaped_la_xml.encode()).digest()

        SignedInfo = XmlBuilder._SignedInfo(Signature, la_digest)

        signed_info_xml = ET.tostring(
            SignedInfo,
            encoding="utf-8",
            short_empty_elements=False
        )

        SignatureValue = ET.SubElement(Signature, "SignatureValue")
        SignatureValue.text = base64.b64encode(
            Crypto.ecc256_sign(signing_key, signed_info_xml)
        ).decode()

        ECCKeyValue = ET.SubElement(
            ET.SubElement(
                ET.SubElement(
                    Signature, "KeyInfo", {
                        "xmlns": "http://www.w3.org/2000/09/xmldsig#"
                    }
                ),
                "KeyValue"
            ), "ECCKeyValue"
        )

        PublicKey = ET.SubElement(ECCKeyValue, "PublicKey")
        PublicKey.text = base64.b64encode(signing_key.public_bytes()).decode()

        return AcquireLicense

    @staticmethod
    def ClientData(cert_chains: List[CertificateChain], ree_features: List[str]) -> str:
        Data = ET.Element("Data")
        CertificateChains = ET.SubElement(Data, "CertificateChains")

        for cert_chain in cert_chains:
            CertificateChainElement = ET.SubElement(CertificateChains, "CertificateChain")
            CertificateChainElement.text = f" {base64.b64encode(cert_chain.dumps()).decode()} "

        Features = ET.SubElement(Data, "Features")
        ET.SubElement(Features, "Feature", {"Name": "AESCBC"})

        REE = ET.SubElement(Features, "REE")
        for ree_feature in ree_features:
            ET.SubElement(REE, ree_feature)

        return ET.tostring(
            Data,
            encoding="utf-8",
            short_empty_elements=False
        ).decode()