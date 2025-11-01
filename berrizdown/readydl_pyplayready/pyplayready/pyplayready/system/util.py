import xml.etree.ElementTree as ET


class Util:
    @staticmethod
    def remove_namespaces(element: ET.Element) -> None:
        for elem in element.iter():
            elem.tag = elem.tag.split("}")[-1]

    @staticmethod
    def un_pad(name: bytes) -> str:
        return name.rstrip(b"\x00").decode("utf-8", errors="ignore")

    @staticmethod
    def to_bytes(n: int) -> bytes:
        byte_len = (n.bit_length() + 7) // 8
        if byte_len % 2 != 0:
            byte_len += 1
        return n.to_bytes(byte_len, "big")
