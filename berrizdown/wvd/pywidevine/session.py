from Crypto.Random import get_random_bytes

from berrizdown.wvd.pywidevine.key import Key
from berrizdown.wvd.pywidevine.license_protocol_pb2 import SignedDrmCertificate


class Session:
    def __init__(self, number: int):
        self.number = number
        self.id = get_random_bytes(16)
        self.service_certificate: SignedDrmCertificate | None = None
        self.context: dict[bytes, tuple[bytes, bytes]] = {}
        self.keys: list[Key] = []


__all__ = ("Session",)
