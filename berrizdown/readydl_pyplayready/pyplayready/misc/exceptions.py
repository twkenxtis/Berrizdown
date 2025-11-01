class PyPlayreadyException(Exception):
    """Exceptions used by pyplayready."""


class TooManySessions(PyPlayreadyException):
    """Too many Sessions are open."""


class InvalidSession(PyPlayreadyException):
    """No Session is open with the specified identifier."""


class InvalidSoapMessage(PyPlayreadyException):
    """The Soap Message is invalid or empty."""


class InvalidPssh(PyPlayreadyException):
    """The Playready PSSH is invalid or empty."""


class InvalidWrmHeader(PyPlayreadyException):
    """The Playready WRMHEADER is invalid or empty."""


class InvalidChecksum(PyPlayreadyException):
    """The Playready WRMHEADER key ID checksum is invalid or empty."""


class InvalidInitData(PyPlayreadyException):
    """The Playready Cenc Header Data is invalid or empty."""


class DeviceMismatch(PyPlayreadyException):
    """The Remote CDMs Device information and the APIs Device information did not match."""


class InvalidXmrLicense(PyPlayreadyException):
    """Unable to parse XMR License."""


class InvalidLicense(PyPlayreadyException):
    """Unable to parse License XML."""


class InvalidCertificate(PyPlayreadyException):
    """The BCert is not correctly formatted."""


class InvalidCertificateChain(PyPlayreadyException):
    """The BCertChain is not correctly formatted."""


class OutdatedDevice(PyPlayreadyException):
    """The PlayReady Device is outdated and does not support a specific operation."""


class ServerException(PyPlayreadyException):
    """Re-casted on the client if found in license response."""


class InvalidRevocationList(PyPlayreadyException):
    """The RevocationList is not correctly formatted."""