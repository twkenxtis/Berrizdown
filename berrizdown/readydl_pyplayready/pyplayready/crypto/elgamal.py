from typing import Tuple

from ecpy.curves import Curve, Point
import secrets


class ElGamal:
    """ElGamal ECC utility using ecpy"""

    curve = Curve.get_curve("secp256r1")

    @staticmethod
    def encrypt(message_point: Point, public_key: Point) -> Tuple[Point, Point]:
        """
        Encrypt a single point with a given public key

        Returns an encrypted point pair
        """
        ephemeral_key = secrets.randbelow(ElGamal.curve.order)
        point1 = ephemeral_key * ElGamal.curve.generator
        point2 = message_point + (ephemeral_key * public_key)
        return point1, point2

    @staticmethod
    def decrypt(encrypted: Tuple[Point, Point], private_key: int) -> Point:
        """
        Decrypt and encrypted point pair with a given private key

        Returns a single decrypted point
        """
        point1, point2 = encrypted
        shared_secret = private_key * point1
        decrypted_message = point2 - shared_secret
        return decrypted_message
