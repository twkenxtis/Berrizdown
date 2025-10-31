# mypy: ignore-errors

from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

AUTOMATIC: LicenseType
DESCRIPTOR: _descriptor.FileDescriptor
HASH_ALGORITHM_SHA_1: HashAlgorithmProto
HASH_ALGORITHM_SHA_256: HashAlgorithmProto
HASH_ALGORITHM_SHA_384: HashAlgorithmProto
HASH_ALGORITHM_UNSPECIFIED: HashAlgorithmProto
OFFLINE: LicenseType
PLATFORM_HARDWARE_VERIFIED: PlatformVerificationStatus
PLATFORM_NO_VERIFICATION: PlatformVerificationStatus
PLATFORM_SECURE_STORAGE_SOFTWARE_VERIFIED: PlatformVerificationStatus
PLATFORM_SOFTWARE_VERIFIED: PlatformVerificationStatus
PLATFORM_TAMPERED: PlatformVerificationStatus
PLATFORM_UNVERIFIED: PlatformVerificationStatus
STREAMING: LicenseType
VERSION_2_0: ProtocolVersion
VERSION_2_1: ProtocolVersion
VERSION_2_2: ProtocolVersion

class ClientIdentification(_message.Message):
    __slots__ = [
        "client_capabilities",
        "client_info",
        "device_credentials",
        "license_counter",
        "provider_client_token",
        "token",
        "type",
        "vmp_data",
    ]
    class TokenType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class ClientCapabilities(_message.Message):
        __slots__ = [
            "analog_output_capabilities",
            "anti_rollback_usage_table",
            "can_disable_analog_output",
            "can_update_srm",
            "client_token",
            "max_hdcp_version",
            "oem_crypto_api_version",
            "resource_rating_tier",
            "session_token",
            "srm_version",
            "supported_certificate_key_type",
            "video_resolution_constraints",
        ]
        class AnalogOutputCapabilities(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = []

        class CertificateKeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = []

        class HdcpVersion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = []

        ANALOG_OUTPUT_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
        ANALOG_OUTPUT_NONE: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_SUPPORTED: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_SUPPORTS_CGMS_A: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_UNKNOWN: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANTI_ROLLBACK_USAGE_TABLE_FIELD_NUMBER: _ClassVar[int]
        CAN_DISABLE_ANALOG_OUTPUT_FIELD_NUMBER: _ClassVar[int]
        CAN_UPDATE_SRM_FIELD_NUMBER: _ClassVar[int]
        CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
        ECC_SECP256R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        ECC_SECP384R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        ECC_SECP521R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        HDCP_NONE: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_NO_DIGITAL_OUTPUT: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V1: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_1: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_2: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_3: ClientIdentification.ClientCapabilities.HdcpVersion
        MAX_HDCP_VERSION_FIELD_NUMBER: _ClassVar[int]
        OEM_CRYPTO_API_VERSION_FIELD_NUMBER: _ClassVar[int]
        RESOURCE_RATING_TIER_FIELD_NUMBER: _ClassVar[int]
        RSA_2048: ClientIdentification.ClientCapabilities.CertificateKeyType
        RSA_3072: ClientIdentification.ClientCapabilities.CertificateKeyType
        SESSION_TOKEN_FIELD_NUMBER: _ClassVar[int]
        SRM_VERSION_FIELD_NUMBER: _ClassVar[int]
        SUPPORTED_CERTIFICATE_KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
        VIDEO_RESOLUTION_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
        analog_output_capabilities: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        anti_rollback_usage_table: bool
        can_disable_analog_output: bool
        can_update_srm: bool
        client_token: bool
        max_hdcp_version: ClientIdentification.ClientCapabilities.HdcpVersion
        oem_crypto_api_version: int
        resource_rating_tier: int
        session_token: bool
        srm_version: int
        supported_certificate_key_type: _containers.RepeatedScalarFieldContainer[ClientIdentification.ClientCapabilities.CertificateKeyType]
        video_resolution_constraints: bool
        def __init__(
            self,
            client_token: bool = ...,
            session_token: bool = ...,
            video_resolution_constraints: bool = ...,
            max_hdcp_version: ClientIdentification.ClientCapabilities.HdcpVersion | str | None = ...,
            oem_crypto_api_version: int | None = ...,
            anti_rollback_usage_table: bool = ...,
            srm_version: int | None = ...,
            can_update_srm: bool = ...,
            supported_certificate_key_type: _Iterable[ClientIdentification.ClientCapabilities.CertificateKeyType | str] | None = ...,
            analog_output_capabilities: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities | str | None = ...,
            can_disable_analog_output: bool = ...,
            resource_rating_tier: int | None = ...,
        ) -> None: ...

    class ClientCredentials(_message.Message):
        __slots__ = ["token", "type"]
        TOKEN_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        token: bytes
        type: ClientIdentification.TokenType
        def __init__(self, type: ClientIdentification.TokenType | str | None = ..., token: bytes | None = ...) -> None: ...

    class NameValue(_message.Message):
        __slots__ = ["name", "value"]
        NAME_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        name: str
        value: str
        def __init__(self, name: str | None = ..., value: str | None = ...) -> None: ...

    CLIENT_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    CLIENT_INFO_FIELD_NUMBER: _ClassVar[int]
    DEVICE_CREDENTIALS_FIELD_NUMBER: _ClassVar[int]
    DRM_DEVICE_CERTIFICATE: ClientIdentification.TokenType
    KEYBOX: ClientIdentification.TokenType
    LICENSE_COUNTER_FIELD_NUMBER: _ClassVar[int]
    OEM_DEVICE_CERTIFICATE: ClientIdentification.TokenType
    PROVIDER_CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ATTESTATION_CERTIFICATE: ClientIdentification.TokenType
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VMP_DATA_FIELD_NUMBER: _ClassVar[int]
    client_capabilities: ClientIdentification.ClientCapabilities
    client_info: _containers.RepeatedCompositeFieldContainer[ClientIdentification.NameValue]
    device_credentials: _containers.RepeatedCompositeFieldContainer[ClientIdentification.ClientCredentials]
    license_counter: int
    provider_client_token: bytes
    token: bytes
    type: ClientIdentification.TokenType
    vmp_data: bytes
    def __init__(
        self,
        type: ClientIdentification.TokenType | str | None = ...,
        token: bytes | None = ...,
        client_info: _Iterable[ClientIdentification.NameValue | _Mapping] | None = ...,
        provider_client_token: bytes | None = ...,
        license_counter: int | None = ...,
        client_capabilities: ClientIdentification.ClientCapabilities | _Mapping | None = ...,
        vmp_data: bytes | None = ...,
        device_credentials: _Iterable[ClientIdentification.ClientCredentials | _Mapping] | None = ...,
    ) -> None: ...

class DrmCertificate(_message.Message):
    __slots__ = [
        "algorithm",
        "creation_time_seconds",
        "encryption_key",
        "expiration_time_seconds",
        "provider_id",
        "public_key",
        "rot_id",
        "serial_number",
        "service_types",
        "system_id",
        "test_device_deprecated",
        "type",
    ]
    class Algorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class ServiceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class EncryptionKey(_message.Message):
        __slots__ = ["algorithm", "public_key"]
        ALGORITHM_FIELD_NUMBER: _ClassVar[int]
        PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
        algorithm: DrmCertificate.Algorithm
        public_key: bytes
        def __init__(
            self,
            public_key: bytes | None = ...,
            algorithm: DrmCertificate.Algorithm | str | None = ...,
        ) -> None: ...

    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    CAS_PROXY_SDK: DrmCertificate.ServiceType
    CREATION_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    DEVICE: DrmCertificate.Type
    DEVICE_MODEL: DrmCertificate.Type
    ECC_SECP256R1: DrmCertificate.Algorithm
    ECC_SECP384R1: DrmCertificate.Algorithm
    ECC_SECP521R1: DrmCertificate.Algorithm
    ENCRYPTION_KEY_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    LICENSE_SERVER_PROXY_SDK: DrmCertificate.ServiceType
    LICENSE_SERVER_SDK: DrmCertificate.ServiceType
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    PROVISIONER: DrmCertificate.Type
    PROVISIONING_SDK: DrmCertificate.ServiceType
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    ROOT: DrmCertificate.Type
    ROT_ID_FIELD_NUMBER: _ClassVar[int]
    RSA: DrmCertificate.Algorithm
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SERVICE: DrmCertificate.Type
    SERVICE_TYPES_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    TEST_DEVICE_DEPRECATED_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_ALGORITHM: DrmCertificate.Algorithm
    UNKNOWN_SERVICE_TYPE: DrmCertificate.ServiceType
    algorithm: DrmCertificate.Algorithm
    creation_time_seconds: int
    encryption_key: DrmCertificate.EncryptionKey
    expiration_time_seconds: int
    provider_id: str
    public_key: bytes
    rot_id: bytes
    serial_number: bytes
    service_types: _containers.RepeatedScalarFieldContainer[DrmCertificate.ServiceType]
    system_id: int
    test_device_deprecated: bool
    type: DrmCertificate.Type
    def __init__(
        self,
        type: DrmCertificate.Type | str | None = ...,
        serial_number: bytes | None = ...,
        creation_time_seconds: int | None = ...,
        expiration_time_seconds: int | None = ...,
        public_key: bytes | None = ...,
        system_id: int | None = ...,
        test_device_deprecated: bool = ...,
        provider_id: str | None = ...,
        service_types: _Iterable[DrmCertificate.ServiceType | str] | None = ...,
        algorithm: DrmCertificate.Algorithm | str | None = ...,
        rot_id: bytes | None = ...,
        encryption_key: DrmCertificate.EncryptionKey | _Mapping | None = ...,
    ) -> None: ...

class EncryptedClientIdentification(_message.Message):
    __slots__ = [
        "encrypted_client_id",
        "encrypted_client_id_iv",
        "encrypted_privacy_key",
        "provider_id",
        "service_certificate_serial_number",
    ]
    ENCRYPTED_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_CLIENT_ID_IV_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_PRIVACY_KEY_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_CERTIFICATE_SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    encrypted_client_id: bytes
    encrypted_client_id_iv: bytes
    encrypted_privacy_key: bytes
    provider_id: str
    service_certificate_serial_number: bytes
    def __init__(
        self,
        provider_id: str | None = ...,
        service_certificate_serial_number: bytes | None = ...,
        encrypted_client_id: bytes | None = ...,
        encrypted_client_id_iv: bytes | None = ...,
        encrypted_privacy_key: bytes | None = ...,
    ) -> None: ...

class FileHashes(_message.Message):
    __slots__ = ["signatures", "signer"]
    class Signature(_message.Message):
        __slots__ = ["SHA512Hash", "filename", "main_exe", "signature", "test_signing"]
        FILENAME_FIELD_NUMBER: _ClassVar[int]
        MAIN_EXE_FIELD_NUMBER: _ClassVar[int]
        SHA512HASH_FIELD_NUMBER: _ClassVar[int]
        SHA512Hash: bytes
        SIGNATURE_FIELD_NUMBER: _ClassVar[int]
        TEST_SIGNING_FIELD_NUMBER: _ClassVar[int]
        filename: str
        main_exe: bool
        signature: bytes
        test_signing: bool
        def __init__(
            self,
            filename: str | None = ...,
            test_signing: bool = ...,
            SHA512Hash: bytes | None = ...,
            main_exe: bool = ...,
            signature: bytes | None = ...,
        ) -> None: ...

    SIGNATURES_FIELD_NUMBER: _ClassVar[int]
    SIGNER_FIELD_NUMBER: _ClassVar[int]
    signatures: _containers.RepeatedCompositeFieldContainer[FileHashes.Signature]
    signer: bytes
    def __init__(
        self,
        signer: bytes | None = ...,
        signatures: _Iterable[FileHashes.Signature | _Mapping] | None = ...,
    ) -> None: ...

class License(_message.Message):
    __slots__ = [
        "group_ids",
        "id",
        "key",
        "license_start_time",
        "platform_verification_status",
        "policy",
        "protection_scheme",
        "provider_client_token",
        "remote_attestation_verified",
        "srm_requirement",
        "srm_update",
    ]
    class KeyContainer(_message.Message):
        __slots__ = [
            "anti_rollback_usage_table",
            "id",
            "iv",
            "key",
            "key_control",
            "level",
            "operator_session_key_permissions",
            "requested_protection",
            "required_protection",
            "track_label",
            "type",
            "video_resolution_constraints",
        ]
        class KeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = []

        class SecurityLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = []

        class KeyControl(_message.Message):
            __slots__ = ["iv", "key_control_block"]
            IV_FIELD_NUMBER: _ClassVar[int]
            KEY_CONTROL_BLOCK_FIELD_NUMBER: _ClassVar[int]
            iv: bytes
            key_control_block: bytes
            def __init__(self, key_control_block: bytes | None = ..., iv: bytes | None = ...) -> None: ...

        class OperatorSessionKeyPermissions(_message.Message):
            __slots__ = ["allow_decrypt", "allow_encrypt", "allow_sign", "allow_signature_verify"]
            ALLOW_DECRYPT_FIELD_NUMBER: _ClassVar[int]
            ALLOW_ENCRYPT_FIELD_NUMBER: _ClassVar[int]
            ALLOW_SIGNATURE_VERIFY_FIELD_NUMBER: _ClassVar[int]
            ALLOW_SIGN_FIELD_NUMBER: _ClassVar[int]
            allow_decrypt: bool
            allow_encrypt: bool
            allow_sign: bool
            allow_signature_verify: bool
            def __init__(
                self,
                allow_encrypt: bool = ...,
                allow_decrypt: bool = ...,
                allow_sign: bool = ...,
                allow_signature_verify: bool = ...,
            ) -> None: ...

        class OutputProtection(_message.Message):
            __slots__ = [
                "cgms_flags",
                "disable_analog_output",
                "disable_digital_output",
                "hdcp",
                "hdcp_srm_rule",
            ]
            class CGMS(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = []

            class HDCP(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = []

            class HdcpSrmRule(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = []

            CGMS_FLAGS_FIELD_NUMBER: _ClassVar[int]
            CGMS_NONE: License.KeyContainer.OutputProtection.CGMS
            COPY_FREE: License.KeyContainer.OutputProtection.CGMS
            COPY_NEVER: License.KeyContainer.OutputProtection.CGMS
            COPY_ONCE: License.KeyContainer.OutputProtection.CGMS
            CURRENT_SRM: License.KeyContainer.OutputProtection.HdcpSrmRule
            DISABLE_ANALOG_OUTPUT_FIELD_NUMBER: _ClassVar[int]
            DISABLE_DIGITAL_OUTPUT_FIELD_NUMBER: _ClassVar[int]
            HDCP_FIELD_NUMBER: _ClassVar[int]
            HDCP_NONE: License.KeyContainer.OutputProtection.HDCP
            HDCP_NO_DIGITAL_OUTPUT: License.KeyContainer.OutputProtection.HDCP
            HDCP_SRM_RULE_FIELD_NUMBER: _ClassVar[int]
            HDCP_SRM_RULE_NONE: License.KeyContainer.OutputProtection.HdcpSrmRule
            HDCP_V1: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_1: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_2: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_3: License.KeyContainer.OutputProtection.HDCP
            cgms_flags: License.KeyContainer.OutputProtection.CGMS
            disable_analog_output: bool
            disable_digital_output: bool
            hdcp: License.KeyContainer.OutputProtection.HDCP
            hdcp_srm_rule: License.KeyContainer.OutputProtection.HdcpSrmRule
            def __init__(
                self,
                hdcp: License.KeyContainer.OutputProtection.HDCP | str | None = ...,
                cgms_flags: License.KeyContainer.OutputProtection.CGMS | str | None = ...,
                hdcp_srm_rule: License.KeyContainer.OutputProtection.HdcpSrmRule | str | None = ...,
                disable_analog_output: bool = ...,
                disable_digital_output: bool = ...,
            ) -> None: ...

        class VideoResolutionConstraint(_message.Message):
            __slots__ = ["max_resolution_pixels", "min_resolution_pixels", "required_protection"]
            MAX_RESOLUTION_PIXELS_FIELD_NUMBER: _ClassVar[int]
            MIN_RESOLUTION_PIXELS_FIELD_NUMBER: _ClassVar[int]
            REQUIRED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
            max_resolution_pixels: int
            min_resolution_pixels: int
            required_protection: License.KeyContainer.OutputProtection
            def __init__(
                self,
                min_resolution_pixels: int | None = ...,
                max_resolution_pixels: int | None = ...,
                required_protection: License.KeyContainer.OutputProtection | _Mapping | None = ...,
            ) -> None: ...

        ANTI_ROLLBACK_USAGE_TABLE_FIELD_NUMBER: _ClassVar[int]
        CONTENT: License.KeyContainer.KeyType
        ENTITLEMENT: License.KeyContainer.KeyType
        HW_SECURE_ALL: License.KeyContainer.SecurityLevel
        HW_SECURE_CRYPTO: License.KeyContainer.SecurityLevel
        HW_SECURE_DECODE: License.KeyContainer.SecurityLevel
        ID_FIELD_NUMBER: _ClassVar[int]
        IV_FIELD_NUMBER: _ClassVar[int]
        KEY_CONTROL: License.KeyContainer.KeyType
        KEY_CONTROL_FIELD_NUMBER: _ClassVar[int]
        KEY_FIELD_NUMBER: _ClassVar[int]
        LEVEL_FIELD_NUMBER: _ClassVar[int]
        OEM_CONTENT: License.KeyContainer.KeyType
        OPERATOR_SESSION: License.KeyContainer.KeyType
        OPERATOR_SESSION_KEY_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
        REQUESTED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
        REQUIRED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
        SIGNING: License.KeyContainer.KeyType
        SW_SECURE_CRYPTO: License.KeyContainer.SecurityLevel
        SW_SECURE_DECODE: License.KeyContainer.SecurityLevel
        TRACK_LABEL_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        VIDEO_RESOLUTION_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
        anti_rollback_usage_table: bool
        id: bytes
        iv: bytes
        key: bytes
        key_control: License.KeyContainer.KeyControl
        level: License.KeyContainer.SecurityLevel
        operator_session_key_permissions: License.KeyContainer.OperatorSessionKeyPermissions
        requested_protection: License.KeyContainer.OutputProtection
        required_protection: License.KeyContainer.OutputProtection
        track_label: str
        type: License.KeyContainer.KeyType
        video_resolution_constraints: _containers.RepeatedCompositeFieldContainer[License.KeyContainer.VideoResolutionConstraint]
        def __init__(
            self,
            id: bytes | None = ...,
            iv: bytes | None = ...,
            key: bytes | None = ...,
            type: License.KeyContainer.KeyType | str | None = ...,
            level: License.KeyContainer.SecurityLevel | str | None = ...,
            required_protection: License.KeyContainer.OutputProtection | _Mapping | None = ...,
            requested_protection: License.KeyContainer.OutputProtection | _Mapping | None = ...,
            key_control: License.KeyContainer.KeyControl | _Mapping | None = ...,
            operator_session_key_permissions: License.KeyContainer.OperatorSessionKeyPermissions | _Mapping | None = ...,
            video_resolution_constraints: _Iterable[License.KeyContainer.VideoResolutionConstraint | _Mapping] | None = ...,
            anti_rollback_usage_table: bool = ...,
            track_label: str | None = ...,
        ) -> None: ...

    class Policy(_message.Message):
        __slots__ = [
            "always_include_client_id",
            "can_persist",
            "can_play",
            "can_renew",
            "license_duration_seconds",
            "play_start_grace_period_seconds",
            "playback_duration_seconds",
            "renew_with_usage",
            "renewal_delay_seconds",
            "renewal_recovery_duration_seconds",
            "renewal_retry_interval_seconds",
            "renewal_server_url",
            "rental_duration_seconds",
            "soft_enforce_playback_duration",
            "soft_enforce_rental_duration",
        ]
        ALWAYS_INCLUDE_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
        CAN_PERSIST_FIELD_NUMBER: _ClassVar[int]
        CAN_PLAY_FIELD_NUMBER: _ClassVar[int]
        CAN_RENEW_FIELD_NUMBER: _ClassVar[int]
        LICENSE_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        PLAYBACK_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        PLAY_START_GRACE_PERIOD_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_DELAY_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_RECOVERY_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_RETRY_INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_SERVER_URL_FIELD_NUMBER: _ClassVar[int]
        RENEW_WITH_USAGE_FIELD_NUMBER: _ClassVar[int]
        RENTAL_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        SOFT_ENFORCE_PLAYBACK_DURATION_FIELD_NUMBER: _ClassVar[int]
        SOFT_ENFORCE_RENTAL_DURATION_FIELD_NUMBER: _ClassVar[int]
        always_include_client_id: bool
        can_persist: bool
        can_play: bool
        can_renew: bool
        license_duration_seconds: int
        play_start_grace_period_seconds: int
        playback_duration_seconds: int
        renew_with_usage: bool
        renewal_delay_seconds: int
        renewal_recovery_duration_seconds: int
        renewal_retry_interval_seconds: int
        renewal_server_url: str
        rental_duration_seconds: int
        soft_enforce_playback_duration: bool
        soft_enforce_rental_duration: bool
        def __init__(
            self,
            can_play: bool = ...,
            can_persist: bool = ...,
            can_renew: bool = ...,
            rental_duration_seconds: int | None = ...,
            playback_duration_seconds: int | None = ...,
            license_duration_seconds: int | None = ...,
            renewal_recovery_duration_seconds: int | None = ...,
            renewal_server_url: str | None = ...,
            renewal_delay_seconds: int | None = ...,
            renewal_retry_interval_seconds: int | None = ...,
            renew_with_usage: bool = ...,
            always_include_client_id: bool = ...,
            play_start_grace_period_seconds: int | None = ...,
            soft_enforce_playback_duration: bool = ...,
            soft_enforce_rental_duration: bool = ...,
        ) -> None: ...

    GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LICENSE_START_TIME_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_VERIFICATION_STATUS_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_SCHEME_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ATTESTATION_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    SRM_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    SRM_UPDATE_FIELD_NUMBER: _ClassVar[int]
    group_ids: _containers.RepeatedScalarFieldContainer[bytes]
    id: LicenseIdentification
    key: _containers.RepeatedCompositeFieldContainer[License.KeyContainer]
    license_start_time: int
    platform_verification_status: PlatformVerificationStatus
    policy: License.Policy
    protection_scheme: int
    provider_client_token: bytes
    remote_attestation_verified: bool
    srm_requirement: bytes
    srm_update: bytes
    def __init__(
        self,
        id: LicenseIdentification | _Mapping | None = ...,
        policy: License.Policy | _Mapping | None = ...,
        key: _Iterable[License.KeyContainer | _Mapping] | None = ...,
        license_start_time: int | None = ...,
        remote_attestation_verified: bool = ...,
        provider_client_token: bytes | None = ...,
        protection_scheme: int | None = ...,
        srm_requirement: bytes | None = ...,
        srm_update: bytes | None = ...,
        platform_verification_status: PlatformVerificationStatus | str | None = ...,
        group_ids: _Iterable[bytes] | None = ...,
    ) -> None: ...

class LicenseIdentification(_message.Message):
    __slots__ = [
        "provider_session_token",
        "purchase_id",
        "request_id",
        "session_id",
        "type",
        "version",
    ]
    PROVIDER_SESSION_TOKEN_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    provider_session_token: bytes
    purchase_id: bytes
    request_id: bytes
    session_id: bytes
    type: LicenseType
    version: int
    def __init__(
        self,
        request_id: bytes | None = ...,
        session_id: bytes | None = ...,
        purchase_id: bytes | None = ...,
        type: LicenseType | str | None = ...,
        version: int | None = ...,
        provider_session_token: bytes | None = ...,
    ) -> None: ...

class LicenseRequest(_message.Message):
    __slots__ = [
        "client_id",
        "content_id",
        "encrypted_client_id",
        "key_control_nonce",
        "key_control_nonce_deprecated",
        "protocol_version",
        "request_time",
        "type",
    ]
    class RequestType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class ContentIdentification(_message.Message):
        __slots__ = ["existing_license", "init_data", "webm_key_id", "widevine_pssh_data"]
        class ExistingLicense(_message.Message):
            __slots__ = [
                "license_id",
                "seconds_since_last_played",
                "seconds_since_started",
                "session_usage_table_entry",
            ]
            LICENSE_ID_FIELD_NUMBER: _ClassVar[int]
            SECONDS_SINCE_LAST_PLAYED_FIELD_NUMBER: _ClassVar[int]
            SECONDS_SINCE_STARTED_FIELD_NUMBER: _ClassVar[int]
            SESSION_USAGE_TABLE_ENTRY_FIELD_NUMBER: _ClassVar[int]
            license_id: LicenseIdentification
            seconds_since_last_played: int
            seconds_since_started: int
            session_usage_table_entry: bytes
            def __init__(
                self,
                license_id: LicenseIdentification | _Mapping | None = ...,
                seconds_since_started: int | None = ...,
                seconds_since_last_played: int | None = ...,
                session_usage_table_entry: bytes | None = ...,
            ) -> None: ...

        class InitData(_message.Message):
            __slots__ = ["init_data", "init_data_type", "license_type", "request_id"]
            class InitDataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = []

            CENC: LicenseRequest.ContentIdentification.InitData.InitDataType
            INIT_DATA_FIELD_NUMBER: _ClassVar[int]
            INIT_DATA_TYPE_FIELD_NUMBER: _ClassVar[int]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            WEBM: LicenseRequest.ContentIdentification.InitData.InitDataType
            init_data: bytes
            init_data_type: LicenseRequest.ContentIdentification.InitData.InitDataType
            license_type: LicenseType
            request_id: bytes
            def __init__(
                self,
                init_data_type: LicenseRequest.ContentIdentification.InitData.InitDataType | str | None = ...,
                init_data: bytes | None = ...,
                license_type: LicenseType | str | None = ...,
                request_id: bytes | None = ...,
            ) -> None: ...

        class WebmKeyId(_message.Message):
            __slots__ = ["header", "license_type", "request_id"]
            HEADER_FIELD_NUMBER: _ClassVar[int]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            header: bytes
            license_type: LicenseType
            request_id: bytes
            def __init__(
                self,
                header: bytes | None = ...,
                license_type: LicenseType | str | None = ...,
                request_id: bytes | None = ...,
            ) -> None: ...

        class WidevinePsshData(_message.Message):
            __slots__ = ["license_type", "pssh_data", "request_id"]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            PSSH_DATA_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            license_type: LicenseType
            pssh_data: _containers.RepeatedScalarFieldContainer[bytes]
            request_id: bytes
            def __init__(
                self,
                pssh_data: _Iterable[bytes] | None = ...,
                license_type: LicenseType | str | None = ...,
                request_id: bytes | None = ...,
            ) -> None: ...

        EXISTING_LICENSE_FIELD_NUMBER: _ClassVar[int]
        INIT_DATA_FIELD_NUMBER: _ClassVar[int]
        WEBM_KEY_ID_FIELD_NUMBER: _ClassVar[int]
        WIDEVINE_PSSH_DATA_FIELD_NUMBER: _ClassVar[int]
        existing_license: LicenseRequest.ContentIdentification.ExistingLicense
        init_data: LicenseRequest.ContentIdentification.InitData
        webm_key_id: LicenseRequest.ContentIdentification.WebmKeyId
        widevine_pssh_data: LicenseRequest.ContentIdentification.WidevinePsshData
        def __init__(
            self,
            widevine_pssh_data: LicenseRequest.ContentIdentification.WidevinePsshData | _Mapping | None = ...,
            webm_key_id: LicenseRequest.ContentIdentification.WebmKeyId | _Mapping | None = ...,
            existing_license: LicenseRequest.ContentIdentification.ExistingLicense | _Mapping | None = ...,
            init_data: LicenseRequest.ContentIdentification.InitData | _Mapping | None = ...,
        ) -> None: ...

    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_CONTROL_NONCE_DEPRECATED_FIELD_NUMBER: _ClassVar[int]
    KEY_CONTROL_NONCE_FIELD_NUMBER: _ClassVar[int]
    NEW: LicenseRequest.RequestType
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    RELEASE: LicenseRequest.RequestType
    RENEWAL: LicenseRequest.RequestType
    REQUEST_TIME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    client_id: ClientIdentification
    content_id: LicenseRequest.ContentIdentification
    encrypted_client_id: EncryptedClientIdentification
    key_control_nonce: int
    key_control_nonce_deprecated: bytes
    protocol_version: ProtocolVersion
    request_time: int
    type: LicenseRequest.RequestType
    def __init__(
        self,
        client_id: ClientIdentification | _Mapping | None = ...,
        content_id: LicenseRequest.ContentIdentification | _Mapping | None = ...,
        type: LicenseRequest.RequestType | str | None = ...,
        request_time: int | None = ...,
        key_control_nonce_deprecated: bytes | None = ...,
        protocol_version: ProtocolVersion | str | None = ...,
        key_control_nonce: int | None = ...,
        encrypted_client_id: EncryptedClientIdentification | _Mapping | None = ...,
    ) -> None: ...

class MetricData(_message.Message):
    __slots__ = ["metric_data", "stage_name"]
    class MetricType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class TypeValue(_message.Message):
        __slots__ = ["type", "value"]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        type: MetricData.MetricType
        value: int
        def __init__(self, type: MetricData.MetricType | str | None = ..., value: int | None = ...) -> None: ...

    LATENCY: MetricData.MetricType
    METRIC_DATA_FIELD_NUMBER: _ClassVar[int]
    STAGE_NAME_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP: MetricData.MetricType
    metric_data: _containers.RepeatedCompositeFieldContainer[MetricData.TypeValue]
    stage_name: str
    def __init__(
        self,
        stage_name: str | None = ...,
        metric_data: _Iterable[MetricData.TypeValue | _Mapping] | None = ...,
    ) -> None: ...

class SignedDrmCertificate(_message.Message):
    __slots__ = ["drm_certificate", "hash_algorithm", "signature", "signer"]
    DRM_CERTIFICATE_FIELD_NUMBER: _ClassVar[int]
    HASH_ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    SIGNER_FIELD_NUMBER: _ClassVar[int]
    drm_certificate: bytes
    hash_algorithm: HashAlgorithmProto
    signature: bytes
    signer: SignedDrmCertificate
    def __init__(
        self,
        drm_certificate: bytes | None = ...,
        signature: bytes | None = ...,
        signer: SignedDrmCertificate | _Mapping | None = ...,
        hash_algorithm: HashAlgorithmProto | str | None = ...,
    ) -> None: ...

class SignedMessage(_message.Message):
    __slots__ = [
        "metric_data",
        "msg",
        "oemcrypto_core_message",
        "remote_attestation",
        "service_version_info",
        "session_key",
        "session_key_type",
        "signature",
        "type",
    ]
    class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class SessionKeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    CAS_LICENSE: SignedMessage.MessageType
    CAS_LICENSE_REQUEST: SignedMessage.MessageType
    EPHERMERAL_ECC_PUBLIC_KEY: SignedMessage.SessionKeyType
    ERROR_RESPONSE: SignedMessage.MessageType
    EXTERNAL_LICENSE: SignedMessage.MessageType
    EXTERNAL_LICENSE_REQUEST: SignedMessage.MessageType
    LICENSE: SignedMessage.MessageType
    LICENSE_REQUEST: SignedMessage.MessageType
    METRIC_DATA_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    OEMCRYPTO_CORE_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ATTESTATION_FIELD_NUMBER: _ClassVar[int]
    SERVICE_CERTIFICATE: SignedMessage.MessageType
    SERVICE_CERTIFICATE_REQUEST: SignedMessage.MessageType
    SERVICE_VERSION_INFO_FIELD_NUMBER: _ClassVar[int]
    SESSION_KEY_FIELD_NUMBER: _ClassVar[int]
    SESSION_KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    SUB_LICENSE: SignedMessage.MessageType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UNDEFINED: SignedMessage.SessionKeyType
    WRAPPED_AES_KEY: SignedMessage.SessionKeyType
    metric_data: _containers.RepeatedCompositeFieldContainer[MetricData]
    msg: bytes
    oemcrypto_core_message: bytes
    remote_attestation: bytes
    service_version_info: VersionInfo
    session_key: bytes
    session_key_type: SignedMessage.SessionKeyType
    signature: bytes
    type: SignedMessage.MessageType
    def __init__(
        self,
        type: SignedMessage.MessageType | str | None = ...,
        msg: bytes | None = ...,
        signature: bytes | None = ...,
        session_key: bytes | None = ...,
        remote_attestation: bytes | None = ...,
        metric_data: _Iterable[MetricData | _Mapping] | None = ...,
        service_version_info: VersionInfo | _Mapping | None = ...,
        session_key_type: SignedMessage.SessionKeyType | str | None = ...,
        oemcrypto_core_message: bytes | None = ...,
    ) -> None: ...

class VersionInfo(_message.Message):
    __slots__ = ["license_sdk_version", "license_service_version"]
    LICENSE_SDK_VERSION_FIELD_NUMBER: _ClassVar[int]
    LICENSE_SERVICE_VERSION_FIELD_NUMBER: _ClassVar[int]
    license_sdk_version: str
    license_service_version: str
    def __init__(self, license_sdk_version: str | None = ..., license_service_version: str | None = ...) -> None: ...

class WidevinePsshData(_message.Message):
    __slots__ = [
        "algorithm",
        "content_id",
        "crypto_period_index",
        "crypto_period_seconds",
        "entitled_keys",
        "group_ids",
        "grouped_license",
        "key_ids",
        "key_sequence",
        "policy",
        "protection_scheme",
        "provider",
        "track_type",
        "type",
        "video_feature",
    ]
    class Algorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class EntitledKey(_message.Message):
        __slots__ = ["entitlement_key_id", "entitlement_key_size_bytes", "iv", "key", "key_id"]
        ENTITLEMENT_KEY_ID_FIELD_NUMBER: _ClassVar[int]
        ENTITLEMENT_KEY_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
        IV_FIELD_NUMBER: _ClassVar[int]
        KEY_FIELD_NUMBER: _ClassVar[int]
        KEY_ID_FIELD_NUMBER: _ClassVar[int]
        entitlement_key_id: bytes
        entitlement_key_size_bytes: int
        iv: bytes
        key: bytes
        key_id: bytes
        def __init__(
            self,
            entitlement_key_id: bytes | None = ...,
            key_id: bytes | None = ...,
            key: bytes | None = ...,
            iv: bytes | None = ...,
            entitlement_key_size_bytes: int | None = ...,
        ) -> None: ...

    AESCTR: WidevinePsshData.Algorithm
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    CRYPTO_PERIOD_INDEX_FIELD_NUMBER: _ClassVar[int]
    CRYPTO_PERIOD_SECONDS_FIELD_NUMBER: _ClassVar[int]
    ENTITLED_KEY: WidevinePsshData.Type
    ENTITLED_KEYS_FIELD_NUMBER: _ClassVar[int]
    ENTITLEMENT: WidevinePsshData.Type
    GROUPED_LICENSE_FIELD_NUMBER: _ClassVar[int]
    GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    KEY_IDS_FIELD_NUMBER: _ClassVar[int]
    KEY_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_SCHEME_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    SINGLE: WidevinePsshData.Type
    TRACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UNENCRYPTED: WidevinePsshData.Algorithm
    VIDEO_FEATURE_FIELD_NUMBER: _ClassVar[int]
    algorithm: WidevinePsshData.Algorithm
    content_id: bytes
    crypto_period_index: int
    crypto_period_seconds: int
    entitled_keys: _containers.RepeatedCompositeFieldContainer[WidevinePsshData.EntitledKey]
    group_ids: _containers.RepeatedScalarFieldContainer[bytes]
    grouped_license: bytes
    key_ids: _containers.RepeatedScalarFieldContainer[bytes]
    key_sequence: int
    policy: str
    protection_scheme: int
    provider: str
    track_type: str
    type: WidevinePsshData.Type
    video_feature: str
    def __init__(
        self,
        key_ids: _Iterable[bytes] | None = ...,
        content_id: bytes | None = ...,
        crypto_period_index: int | None = ...,
        protection_scheme: int | None = ...,
        crypto_period_seconds: int | None = ...,
        type: WidevinePsshData.Type | str | None = ...,
        key_sequence: int | None = ...,
        group_ids: _Iterable[bytes] | None = ...,
        entitled_keys: _Iterable[WidevinePsshData.EntitledKey | _Mapping] | None = ...,
        video_feature: str | None = ...,
        algorithm: WidevinePsshData.Algorithm | str | None = ...,
        provider: str | None = ...,
        track_type: str | None = ...,
        policy: str | None = ...,
        grouped_license: bytes | None = ...,
    ) -> None: ...

class LicenseType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class PlatformVerificationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class ProtocolVersion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class HashAlgorithmProto(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
