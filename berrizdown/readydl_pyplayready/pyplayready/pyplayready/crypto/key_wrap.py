from Crypto.Cipher import AES
from Crypto.Hash import CMAC
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap


def derive_wrapping_key() -> bytes:
    """
    NIST SP 800-108 (Rev. 1)
    "Recommendation for Key Derivation Using Pseudorandom Functions"

    https://doi.org/10.6028/NIST.SP.800-108r1
    """

    KeyDerivationCertificatePrivateKeysWrap = bytes(
        [
            0x9C,
            0xE9,
            0x34,
            0x32,
            0xC7,
            0xD7,
            0x40,
            0x16,
            0xBA,
            0x68,
            0x47,
            0x63,
            0xF8,
            0x01,
            0xE1,
            0x36,
        ]
    )

    CTK_TEST = bytes(
        [
            0x8B,
            0x22,
            0x2F,
            0xFD,
            0x1E,
            0x76,
            0x19,
            0x56,
            0x59,
            0xCF,
            0x27,
            0x03,
            0x89,
            0x8C,
            0x42,
            0x7F,
        ]
    )

    cmac = CMAC.new(CTK_TEST, ciphermod=AES)

    cmac.update(
        bytes(
            [
                1,  # Iterations
                *KeyDerivationCertificatePrivateKeysWrap,
                0,  # Separator
                *bytes(16),  # Context
                0,
                128,  # Length in bits of return value
            ]
        )
    )

    derived_wrapping_key = cmac.digest()

    return derived_wrapping_key


def unwrap_wrapped_key(wrapped_key: bytes) -> bytes:
    """
    IETF RFC 3394
    "Advanced Encryption Standard (AES) Key Wrap Algorithm"

    https://www.rfc-editor.org/rfc/rfc3394
    """

    wrapping_key = derive_wrapping_key()
    unwrapped_key = aes_key_unwrap(wrapping_key, wrapped_key)

    # bytes 0 -32: unwrapped key
    # bytes 32-48: random bytes

    return unwrapped_key[:32]
