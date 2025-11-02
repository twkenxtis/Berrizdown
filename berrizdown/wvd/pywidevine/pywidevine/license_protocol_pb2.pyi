from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LicenseType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STREAMING: _ClassVar[LicenseType]
    OFFLINE: _ClassVar[LicenseType]
    AUTOMATIC: _ClassVar[LicenseType]

class PlatformVerificationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLATFORM_UNVERIFIED: _ClassVar[PlatformVerificationStatus]
    PLATFORM_TAMPERED: _ClassVar[PlatformVerificationStatus]
    PLATFORM_SOFTWARE_VERIFIED: _ClassVar[PlatformVerificationStatus]
    PLATFORM_HARDWARE_VERIFIED: _ClassVar[PlatformVerificationStatus]
    PLATFORM_NO_VERIFICATION: _ClassVar[PlatformVerificationStatus]
    PLATFORM_SECURE_STORAGE_SOFTWARE_VERIFIED: _ClassVar[PlatformVerificationStatus]

class ProtocolVersion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VERSION_2_0: _ClassVar[ProtocolVersion]
    VERSION_2_1: _ClassVar[ProtocolVersion]
    VERSION_2_2: _ClassVar[ProtocolVersion]

class HashAlgorithmProto(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HASH_ALGORITHM_UNSPECIFIED: _ClassVar[HashAlgorithmProto]
    HASH_ALGORITHM_SHA_1: _ClassVar[HashAlgorithmProto]
    HASH_ALGORITHM_SHA_256: _ClassVar[HashAlgorithmProto]
    HASH_ALGORITHM_SHA_384: _ClassVar[HashAlgorithmProto]
STREAMING: LicenseType
OFFLINE: LicenseType
AUTOMATIC: LicenseType
PLATFORM_UNVERIFIED: PlatformVerificationStatus
PLATFORM_TAMPERED: PlatformVerificationStatus
PLATFORM_SOFTWARE_VERIFIED: PlatformVerificationStatus
PLATFORM_HARDWARE_VERIFIED: PlatformVerificationStatus
PLATFORM_NO_VERIFICATION: PlatformVerificationStatus
PLATFORM_SECURE_STORAGE_SOFTWARE_VERIFIED: PlatformVerificationStatus
VERSION_2_0: ProtocolVersion
VERSION_2_1: ProtocolVersion
VERSION_2_2: ProtocolVersion
HASH_ALGORITHM_UNSPECIFIED: HashAlgorithmProto
HASH_ALGORITHM_SHA_1: HashAlgorithmProto
HASH_ALGORITHM_SHA_256: HashAlgorithmProto
HASH_ALGORITHM_SHA_384: HashAlgorithmProto

class LicenseIdentification(_message.Message):
    __slots__ = ("request_id", "session_id", "purchase_id", "type", "version", "provider_session_token")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_SESSION_TOKEN_FIELD_NUMBER: _ClassVar[int]
    request_id: bytes
    session_id: bytes
    purchase_id: bytes
    type: LicenseType
    version: int
    provider_session_token: bytes
    def __init__(self, request_id: _Optional[bytes] = ..., session_id: _Optional[bytes] = ..., purchase_id: _Optional[bytes] = ..., type: _Optional[_Union[LicenseType, str]] = ..., version: _Optional[int] = ..., provider_session_token: _Optional[bytes] = ...) -> None: ...

class License(_message.Message):
    __slots__ = ("id", "policy", "key", "license_start_time", "remote_attestation_verified", "provider_client_token", "protection_scheme", "srm_requirement", "srm_update", "platform_verification_status", "group_ids")
    class Policy(_message.Message):
        __slots__ = ("can_play", "can_persist", "can_renew", "rental_duration_seconds", "playback_duration_seconds", "license_duration_seconds", "renewal_recovery_duration_seconds", "renewal_server_url", "renewal_delay_seconds", "renewal_retry_interval_seconds", "renew_with_usage", "always_include_client_id", "play_start_grace_period_seconds", "soft_enforce_playback_duration", "soft_enforce_rental_duration")
        CAN_PLAY_FIELD_NUMBER: _ClassVar[int]
        CAN_PERSIST_FIELD_NUMBER: _ClassVar[int]
        CAN_RENEW_FIELD_NUMBER: _ClassVar[int]
        RENTAL_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        PLAYBACK_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        LICENSE_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_RECOVERY_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_SERVER_URL_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_DELAY_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEWAL_RETRY_INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
        RENEW_WITH_USAGE_FIELD_NUMBER: _ClassVar[int]
        ALWAYS_INCLUDE_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
        PLAY_START_GRACE_PERIOD_SECONDS_FIELD_NUMBER: _ClassVar[int]
        SOFT_ENFORCE_PLAYBACK_DURATION_FIELD_NUMBER: _ClassVar[int]
        SOFT_ENFORCE_RENTAL_DURATION_FIELD_NUMBER: _ClassVar[int]
        can_play: bool
        can_persist: bool
        can_renew: bool
        rental_duration_seconds: int
        playback_duration_seconds: int
        license_duration_seconds: int
        renewal_recovery_duration_seconds: int
        renewal_server_url: str
        renewal_delay_seconds: int
        renewal_retry_interval_seconds: int
        renew_with_usage: bool
        always_include_client_id: bool
        play_start_grace_period_seconds: int
        soft_enforce_playback_duration: bool
        soft_enforce_rental_duration: bool
        def __init__(self, can_play: bool = ..., can_persist: bool = ..., can_renew: bool = ..., rental_duration_seconds: _Optional[int] = ..., playback_duration_seconds: _Optional[int] = ..., license_duration_seconds: _Optional[int] = ..., renewal_recovery_duration_seconds: _Optional[int] = ..., renewal_server_url: _Optional[str] = ..., renewal_delay_seconds: _Optional[int] = ..., renewal_retry_interval_seconds: _Optional[int] = ..., renew_with_usage: bool = ..., always_include_client_id: bool = ..., play_start_grace_period_seconds: _Optional[int] = ..., soft_enforce_playback_duration: bool = ..., soft_enforce_rental_duration: bool = ...) -> None: ...
    class KeyContainer(_message.Message):
        __slots__ = ("id", "iv", "key", "type", "level", "required_protection", "requested_protection", "key_control", "operator_session_key_permissions", "video_resolution_constraints", "anti_rollback_usage_table", "track_label")
        class KeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            SIGNING: _ClassVar[License.KeyContainer.KeyType]
            CONTENT: _ClassVar[License.KeyContainer.KeyType]
            KEY_CONTROL: _ClassVar[License.KeyContainer.KeyType]
            OPERATOR_SESSION: _ClassVar[License.KeyContainer.KeyType]
            ENTITLEMENT: _ClassVar[License.KeyContainer.KeyType]
            OEM_CONTENT: _ClassVar[License.KeyContainer.KeyType]
        SIGNING: License.KeyContainer.KeyType
        CONTENT: License.KeyContainer.KeyType
        KEY_CONTROL: License.KeyContainer.KeyType
        OPERATOR_SESSION: License.KeyContainer.KeyType
        ENTITLEMENT: License.KeyContainer.KeyType
        OEM_CONTENT: License.KeyContainer.KeyType
        class SecurityLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            SW_SECURE_CRYPTO: _ClassVar[License.KeyContainer.SecurityLevel]
            SW_SECURE_DECODE: _ClassVar[License.KeyContainer.SecurityLevel]
            HW_SECURE_CRYPTO: _ClassVar[License.KeyContainer.SecurityLevel]
            HW_SECURE_DECODE: _ClassVar[License.KeyContainer.SecurityLevel]
            HW_SECURE_ALL: _ClassVar[License.KeyContainer.SecurityLevel]
        SW_SECURE_CRYPTO: License.KeyContainer.SecurityLevel
        SW_SECURE_DECODE: License.KeyContainer.SecurityLevel
        HW_SECURE_CRYPTO: License.KeyContainer.SecurityLevel
        HW_SECURE_DECODE: License.KeyContainer.SecurityLevel
        HW_SECURE_ALL: License.KeyContainer.SecurityLevel
        class KeyControl(_message.Message):
            __slots__ = ("key_control_block", "iv")
            KEY_CONTROL_BLOCK_FIELD_NUMBER: _ClassVar[int]
            IV_FIELD_NUMBER: _ClassVar[int]
            key_control_block: bytes
            iv: bytes
            def __init__(self, key_control_block: _Optional[bytes] = ..., iv: _Optional[bytes] = ...) -> None: ...
        class OutputProtection(_message.Message):
            __slots__ = ("hdcp", "cgms_flags", "hdcp_srm_rule", "disable_analog_output", "disable_digital_output")
            class HDCP(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                HDCP_NONE: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_V1: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_V2: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_V2_1: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_V2_2: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_V2_3: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
                HDCP_NO_DIGITAL_OUTPUT: _ClassVar[License.KeyContainer.OutputProtection.HDCP]
            HDCP_NONE: License.KeyContainer.OutputProtection.HDCP
            HDCP_V1: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_1: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_2: License.KeyContainer.OutputProtection.HDCP
            HDCP_V2_3: License.KeyContainer.OutputProtection.HDCP
            HDCP_NO_DIGITAL_OUTPUT: License.KeyContainer.OutputProtection.HDCP
            class CGMS(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                CGMS_NONE: _ClassVar[License.KeyContainer.OutputProtection.CGMS]
                COPY_FREE: _ClassVar[License.KeyContainer.OutputProtection.CGMS]
                COPY_ONCE: _ClassVar[License.KeyContainer.OutputProtection.CGMS]
                COPY_NEVER: _ClassVar[License.KeyContainer.OutputProtection.CGMS]
            CGMS_NONE: License.KeyContainer.OutputProtection.CGMS
            COPY_FREE: License.KeyContainer.OutputProtection.CGMS
            COPY_ONCE: License.KeyContainer.OutputProtection.CGMS
            COPY_NEVER: License.KeyContainer.OutputProtection.CGMS
            class HdcpSrmRule(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                HDCP_SRM_RULE_NONE: _ClassVar[License.KeyContainer.OutputProtection.HdcpSrmRule]
                CURRENT_SRM: _ClassVar[License.KeyContainer.OutputProtection.HdcpSrmRule]
            HDCP_SRM_RULE_NONE: License.KeyContainer.OutputProtection.HdcpSrmRule
            CURRENT_SRM: License.KeyContainer.OutputProtection.HdcpSrmRule
            HDCP_FIELD_NUMBER: _ClassVar[int]
            CGMS_FLAGS_FIELD_NUMBER: _ClassVar[int]
            HDCP_SRM_RULE_FIELD_NUMBER: _ClassVar[int]
            DISABLE_ANALOG_OUTPUT_FIELD_NUMBER: _ClassVar[int]
            DISABLE_DIGITAL_OUTPUT_FIELD_NUMBER: _ClassVar[int]
            hdcp: License.KeyContainer.OutputProtection.HDCP
            cgms_flags: License.KeyContainer.OutputProtection.CGMS
            hdcp_srm_rule: License.KeyContainer.OutputProtection.HdcpSrmRule
            disable_analog_output: bool
            disable_digital_output: bool
            def __init__(self, hdcp: _Optional[_Union[License.KeyContainer.OutputProtection.HDCP, str]] = ..., cgms_flags: _Optional[_Union[License.KeyContainer.OutputProtection.CGMS, str]] = ..., hdcp_srm_rule: _Optional[_Union[License.KeyContainer.OutputProtection.HdcpSrmRule, str]] = ..., disable_analog_output: bool = ..., disable_digital_output: bool = ...) -> None: ...
        class VideoResolutionConstraint(_message.Message):
            __slots__ = ("min_resolution_pixels", "max_resolution_pixels", "required_protection")
            MIN_RESOLUTION_PIXELS_FIELD_NUMBER: _ClassVar[int]
            MAX_RESOLUTION_PIXELS_FIELD_NUMBER: _ClassVar[int]
            REQUIRED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
            min_resolution_pixels: int
            max_resolution_pixels: int
            required_protection: License.KeyContainer.OutputProtection
            def __init__(self, min_resolution_pixels: _Optional[int] = ..., max_resolution_pixels: _Optional[int] = ..., required_protection: _Optional[_Union[License.KeyContainer.OutputProtection, _Mapping]] = ...) -> None: ...
        class OperatorSessionKeyPermissions(_message.Message):
            __slots__ = ("allow_encrypt", "allow_decrypt", "allow_sign", "allow_signature_verify")
            ALLOW_ENCRYPT_FIELD_NUMBER: _ClassVar[int]
            ALLOW_DECRYPT_FIELD_NUMBER: _ClassVar[int]
            ALLOW_SIGN_FIELD_NUMBER: _ClassVar[int]
            ALLOW_SIGNATURE_VERIFY_FIELD_NUMBER: _ClassVar[int]
            allow_encrypt: bool
            allow_decrypt: bool
            allow_sign: bool
            allow_signature_verify: bool
            def __init__(self, allow_encrypt: bool = ..., allow_decrypt: bool = ..., allow_sign: bool = ..., allow_signature_verify: bool = ...) -> None: ...
        ID_FIELD_NUMBER: _ClassVar[int]
        IV_FIELD_NUMBER: _ClassVar[int]
        KEY_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        LEVEL_FIELD_NUMBER: _ClassVar[int]
        REQUIRED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
        REQUESTED_PROTECTION_FIELD_NUMBER: _ClassVar[int]
        KEY_CONTROL_FIELD_NUMBER: _ClassVar[int]
        OPERATOR_SESSION_KEY_PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
        VIDEO_RESOLUTION_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
        ANTI_ROLLBACK_USAGE_TABLE_FIELD_NUMBER: _ClassVar[int]
        TRACK_LABEL_FIELD_NUMBER: _ClassVar[int]
        id: bytes
        iv: bytes
        key: bytes
        type: License.KeyContainer.KeyType
        level: License.KeyContainer.SecurityLevel
        required_protection: License.KeyContainer.OutputProtection
        requested_protection: License.KeyContainer.OutputProtection
        key_control: License.KeyContainer.KeyControl
        operator_session_key_permissions: License.KeyContainer.OperatorSessionKeyPermissions
        video_resolution_constraints: _containers.RepeatedCompositeFieldContainer[License.KeyContainer.VideoResolutionConstraint]
        anti_rollback_usage_table: bool
        track_label: str
        def __init__(self, id: _Optional[bytes] = ..., iv: _Optional[bytes] = ..., key: _Optional[bytes] = ..., type: _Optional[_Union[License.KeyContainer.KeyType, str]] = ..., level: _Optional[_Union[License.KeyContainer.SecurityLevel, str]] = ..., required_protection: _Optional[_Union[License.KeyContainer.OutputProtection, _Mapping]] = ..., requested_protection: _Optional[_Union[License.KeyContainer.OutputProtection, _Mapping]] = ..., key_control: _Optional[_Union[License.KeyContainer.KeyControl, _Mapping]] = ..., operator_session_key_permissions: _Optional[_Union[License.KeyContainer.OperatorSessionKeyPermissions, _Mapping]] = ..., video_resolution_constraints: _Optional[_Iterable[_Union[License.KeyContainer.VideoResolutionConstraint, _Mapping]]] = ..., anti_rollback_usage_table: bool = ..., track_label: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LICENSE_START_TIME_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ATTESTATION_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_SCHEME_FIELD_NUMBER: _ClassVar[int]
    SRM_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    SRM_UPDATE_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_VERIFICATION_STATUS_FIELD_NUMBER: _ClassVar[int]
    GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    id: LicenseIdentification
    policy: License.Policy
    key: _containers.RepeatedCompositeFieldContainer[License.KeyContainer]
    license_start_time: int
    remote_attestation_verified: bool
    provider_client_token: bytes
    protection_scheme: int
    srm_requirement: bytes
    srm_update: bytes
    platform_verification_status: PlatformVerificationStatus
    group_ids: _containers.RepeatedScalarFieldContainer[bytes]
    def __init__(self, id: _Optional[_Union[LicenseIdentification, _Mapping]] = ..., policy: _Optional[_Union[License.Policy, _Mapping]] = ..., key: _Optional[_Iterable[_Union[License.KeyContainer, _Mapping]]] = ..., license_start_time: _Optional[int] = ..., remote_attestation_verified: bool = ..., provider_client_token: _Optional[bytes] = ..., protection_scheme: _Optional[int] = ..., srm_requirement: _Optional[bytes] = ..., srm_update: _Optional[bytes] = ..., platform_verification_status: _Optional[_Union[PlatformVerificationStatus, str]] = ..., group_ids: _Optional[_Iterable[bytes]] = ...) -> None: ...

class LicenseRequest(_message.Message):
    __slots__ = ("client_id", "content_id", "type", "request_time", "key_control_nonce_deprecated", "protocol_version", "key_control_nonce", "encrypted_client_id")
    class RequestType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NEW: _ClassVar[LicenseRequest.RequestType]
        RENEWAL: _ClassVar[LicenseRequest.RequestType]
        RELEASE: _ClassVar[LicenseRequest.RequestType]
    NEW: LicenseRequest.RequestType
    RENEWAL: LicenseRequest.RequestType
    RELEASE: LicenseRequest.RequestType
    class ContentIdentification(_message.Message):
        __slots__ = ("widevine_pssh_data", "webm_key_id", "existing_license", "init_data")
        class WidevinePsshData(_message.Message):
            __slots__ = ("pssh_data", "license_type", "request_id")
            PSSH_DATA_FIELD_NUMBER: _ClassVar[int]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            pssh_data: _containers.RepeatedScalarFieldContainer[bytes]
            license_type: LicenseType
            request_id: bytes
            def __init__(self, pssh_data: _Optional[_Iterable[bytes]] = ..., license_type: _Optional[_Union[LicenseType, str]] = ..., request_id: _Optional[bytes] = ...) -> None: ...
        class WebmKeyId(_message.Message):
            __slots__ = ("header", "license_type", "request_id")
            HEADER_FIELD_NUMBER: _ClassVar[int]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            header: bytes
            license_type: LicenseType
            request_id: bytes
            def __init__(self, header: _Optional[bytes] = ..., license_type: _Optional[_Union[LicenseType, str]] = ..., request_id: _Optional[bytes] = ...) -> None: ...
        class ExistingLicense(_message.Message):
            __slots__ = ("license_id", "seconds_since_started", "seconds_since_last_played", "session_usage_table_entry")
            LICENSE_ID_FIELD_NUMBER: _ClassVar[int]
            SECONDS_SINCE_STARTED_FIELD_NUMBER: _ClassVar[int]
            SECONDS_SINCE_LAST_PLAYED_FIELD_NUMBER: _ClassVar[int]
            SESSION_USAGE_TABLE_ENTRY_FIELD_NUMBER: _ClassVar[int]
            license_id: LicenseIdentification
            seconds_since_started: int
            seconds_since_last_played: int
            session_usage_table_entry: bytes
            def __init__(self, license_id: _Optional[_Union[LicenseIdentification, _Mapping]] = ..., seconds_since_started: _Optional[int] = ..., seconds_since_last_played: _Optional[int] = ..., session_usage_table_entry: _Optional[bytes] = ...) -> None: ...
        class InitData(_message.Message):
            __slots__ = ("init_data_type", "init_data", "license_type", "request_id")
            class InitDataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                CENC: _ClassVar[LicenseRequest.ContentIdentification.InitData.InitDataType]
                WEBM: _ClassVar[LicenseRequest.ContentIdentification.InitData.InitDataType]
            CENC: LicenseRequest.ContentIdentification.InitData.InitDataType
            WEBM: LicenseRequest.ContentIdentification.InitData.InitDataType
            INIT_DATA_TYPE_FIELD_NUMBER: _ClassVar[int]
            INIT_DATA_FIELD_NUMBER: _ClassVar[int]
            LICENSE_TYPE_FIELD_NUMBER: _ClassVar[int]
            REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
            init_data_type: LicenseRequest.ContentIdentification.InitData.InitDataType
            init_data: bytes
            license_type: LicenseType
            request_id: bytes
            def __init__(self, init_data_type: _Optional[_Union[LicenseRequest.ContentIdentification.InitData.InitDataType, str]] = ..., init_data: _Optional[bytes] = ..., license_type: _Optional[_Union[LicenseType, str]] = ..., request_id: _Optional[bytes] = ...) -> None: ...
        WIDEVINE_PSSH_DATA_FIELD_NUMBER: _ClassVar[int]
        WEBM_KEY_ID_FIELD_NUMBER: _ClassVar[int]
        EXISTING_LICENSE_FIELD_NUMBER: _ClassVar[int]
        INIT_DATA_FIELD_NUMBER: _ClassVar[int]
        widevine_pssh_data: LicenseRequest.ContentIdentification.WidevinePsshData
        webm_key_id: LicenseRequest.ContentIdentification.WebmKeyId
        existing_license: LicenseRequest.ContentIdentification.ExistingLicense
        init_data: LicenseRequest.ContentIdentification.InitData
        def __init__(self, widevine_pssh_data: _Optional[_Union[LicenseRequest.ContentIdentification.WidevinePsshData, _Mapping]] = ..., webm_key_id: _Optional[_Union[LicenseRequest.ContentIdentification.WebmKeyId, _Mapping]] = ..., existing_license: _Optional[_Union[LicenseRequest.ContentIdentification.ExistingLicense, _Mapping]] = ..., init_data: _Optional[_Union[LicenseRequest.ContentIdentification.InitData, _Mapping]] = ...) -> None: ...
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUEST_TIME_FIELD_NUMBER: _ClassVar[int]
    KEY_CONTROL_NONCE_DEPRECATED_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    KEY_CONTROL_NONCE_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    client_id: ClientIdentification
    content_id: LicenseRequest.ContentIdentification
    type: LicenseRequest.RequestType
    request_time: int
    key_control_nonce_deprecated: bytes
    protocol_version: ProtocolVersion
    key_control_nonce: int
    encrypted_client_id: EncryptedClientIdentification
    def __init__(self, client_id: _Optional[_Union[ClientIdentification, _Mapping]] = ..., content_id: _Optional[_Union[LicenseRequest.ContentIdentification, _Mapping]] = ..., type: _Optional[_Union[LicenseRequest.RequestType, str]] = ..., request_time: _Optional[int] = ..., key_control_nonce_deprecated: _Optional[bytes] = ..., protocol_version: _Optional[_Union[ProtocolVersion, str]] = ..., key_control_nonce: _Optional[int] = ..., encrypted_client_id: _Optional[_Union[EncryptedClientIdentification, _Mapping]] = ...) -> None: ...

class MetricData(_message.Message):
    __slots__ = ("stage_name", "metric_data")
    class MetricType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        LATENCY: _ClassVar[MetricData.MetricType]
        TIMESTAMP: _ClassVar[MetricData.MetricType]
    LATENCY: MetricData.MetricType
    TIMESTAMP: MetricData.MetricType
    class TypeValue(_message.Message):
        __slots__ = ("type", "value")
        TYPE_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        type: MetricData.MetricType
        value: int
        def __init__(self, type: _Optional[_Union[MetricData.MetricType, str]] = ..., value: _Optional[int] = ...) -> None: ...
    STAGE_NAME_FIELD_NUMBER: _ClassVar[int]
    METRIC_DATA_FIELD_NUMBER: _ClassVar[int]
    stage_name: str
    metric_data: _containers.RepeatedCompositeFieldContainer[MetricData.TypeValue]
    def __init__(self, stage_name: _Optional[str] = ..., metric_data: _Optional[_Iterable[_Union[MetricData.TypeValue, _Mapping]]] = ...) -> None: ...

class VersionInfo(_message.Message):
    __slots__ = ("license_sdk_version", "license_service_version")
    LICENSE_SDK_VERSION_FIELD_NUMBER: _ClassVar[int]
    LICENSE_SERVICE_VERSION_FIELD_NUMBER: _ClassVar[int]
    license_sdk_version: str
    license_service_version: str
    def __init__(self, license_sdk_version: _Optional[str] = ..., license_service_version: _Optional[str] = ...) -> None: ...

class SignedMessage(_message.Message):
    __slots__ = ("type", "msg", "signature", "session_key", "remote_attestation", "metric_data", "service_version_info", "session_key_type", "oemcrypto_core_message")
    class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        LICENSE_REQUEST: _ClassVar[SignedMessage.MessageType]
        LICENSE: _ClassVar[SignedMessage.MessageType]
        ERROR_RESPONSE: _ClassVar[SignedMessage.MessageType]
        SERVICE_CERTIFICATE_REQUEST: _ClassVar[SignedMessage.MessageType]
        SERVICE_CERTIFICATE: _ClassVar[SignedMessage.MessageType]
        SUB_LICENSE: _ClassVar[SignedMessage.MessageType]
        CAS_LICENSE_REQUEST: _ClassVar[SignedMessage.MessageType]
        CAS_LICENSE: _ClassVar[SignedMessage.MessageType]
        EXTERNAL_LICENSE_REQUEST: _ClassVar[SignedMessage.MessageType]
        EXTERNAL_LICENSE: _ClassVar[SignedMessage.MessageType]
    LICENSE_REQUEST: SignedMessage.MessageType
    LICENSE: SignedMessage.MessageType
    ERROR_RESPONSE: SignedMessage.MessageType
    SERVICE_CERTIFICATE_REQUEST: SignedMessage.MessageType
    SERVICE_CERTIFICATE: SignedMessage.MessageType
    SUB_LICENSE: SignedMessage.MessageType
    CAS_LICENSE_REQUEST: SignedMessage.MessageType
    CAS_LICENSE: SignedMessage.MessageType
    EXTERNAL_LICENSE_REQUEST: SignedMessage.MessageType
    EXTERNAL_LICENSE: SignedMessage.MessageType
    class SessionKeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNDEFINED: _ClassVar[SignedMessage.SessionKeyType]
        WRAPPED_AES_KEY: _ClassVar[SignedMessage.SessionKeyType]
        EPHERMERAL_ECC_PUBLIC_KEY: _ClassVar[SignedMessage.SessionKeyType]
    UNDEFINED: SignedMessage.SessionKeyType
    WRAPPED_AES_KEY: SignedMessage.SessionKeyType
    EPHERMERAL_ECC_PUBLIC_KEY: SignedMessage.SessionKeyType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    SESSION_KEY_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ATTESTATION_FIELD_NUMBER: _ClassVar[int]
    METRIC_DATA_FIELD_NUMBER: _ClassVar[int]
    SERVICE_VERSION_INFO_FIELD_NUMBER: _ClassVar[int]
    SESSION_KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
    OEMCRYPTO_CORE_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    type: SignedMessage.MessageType
    msg: bytes
    signature: bytes
    session_key: bytes
    remote_attestation: bytes
    metric_data: _containers.RepeatedCompositeFieldContainer[MetricData]
    service_version_info: VersionInfo
    session_key_type: SignedMessage.SessionKeyType
    oemcrypto_core_message: bytes
    def __init__(self, type: _Optional[_Union[SignedMessage.MessageType, str]] = ..., msg: _Optional[bytes] = ..., signature: _Optional[bytes] = ..., session_key: _Optional[bytes] = ..., remote_attestation: _Optional[bytes] = ..., metric_data: _Optional[_Iterable[_Union[MetricData, _Mapping]]] = ..., service_version_info: _Optional[_Union[VersionInfo, _Mapping]] = ..., session_key_type: _Optional[_Union[SignedMessage.SessionKeyType, str]] = ..., oemcrypto_core_message: _Optional[bytes] = ...) -> None: ...

class ClientIdentification(_message.Message):
    __slots__ = ("type", "token", "client_info", "provider_client_token", "license_counter", "client_capabilities", "vmp_data", "device_credentials")
    class TokenType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KEYBOX: _ClassVar[ClientIdentification.TokenType]
        DRM_DEVICE_CERTIFICATE: _ClassVar[ClientIdentification.TokenType]
        REMOTE_ATTESTATION_CERTIFICATE: _ClassVar[ClientIdentification.TokenType]
        OEM_DEVICE_CERTIFICATE: _ClassVar[ClientIdentification.TokenType]
    KEYBOX: ClientIdentification.TokenType
    DRM_DEVICE_CERTIFICATE: ClientIdentification.TokenType
    REMOTE_ATTESTATION_CERTIFICATE: ClientIdentification.TokenType
    OEM_DEVICE_CERTIFICATE: ClientIdentification.TokenType
    class NameValue(_message.Message):
        __slots__ = ("name", "value")
        NAME_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        name: str
        value: str
        def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ClientCapabilities(_message.Message):
        __slots__ = ("client_token", "session_token", "video_resolution_constraints", "max_hdcp_version", "oem_crypto_api_version", "anti_rollback_usage_table", "srm_version", "can_update_srm", "supported_certificate_key_type", "analog_output_capabilities", "can_disable_analog_output", "resource_rating_tier")
        class HdcpVersion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            HDCP_NONE: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_V1: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_V2: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_V2_1: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_V2_2: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_V2_3: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
            HDCP_NO_DIGITAL_OUTPUT: _ClassVar[ClientIdentification.ClientCapabilities.HdcpVersion]
        HDCP_NONE: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V1: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_1: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_2: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_V2_3: ClientIdentification.ClientCapabilities.HdcpVersion
        HDCP_NO_DIGITAL_OUTPUT: ClientIdentification.ClientCapabilities.HdcpVersion
        class CertificateKeyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            RSA_2048: _ClassVar[ClientIdentification.ClientCapabilities.CertificateKeyType]
            RSA_3072: _ClassVar[ClientIdentification.ClientCapabilities.CertificateKeyType]
            ECC_SECP256R1: _ClassVar[ClientIdentification.ClientCapabilities.CertificateKeyType]
            ECC_SECP384R1: _ClassVar[ClientIdentification.ClientCapabilities.CertificateKeyType]
            ECC_SECP521R1: _ClassVar[ClientIdentification.ClientCapabilities.CertificateKeyType]
        RSA_2048: ClientIdentification.ClientCapabilities.CertificateKeyType
        RSA_3072: ClientIdentification.ClientCapabilities.CertificateKeyType
        ECC_SECP256R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        ECC_SECP384R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        ECC_SECP521R1: ClientIdentification.ClientCapabilities.CertificateKeyType
        class AnalogOutputCapabilities(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ANALOG_OUTPUT_UNKNOWN: _ClassVar[ClientIdentification.ClientCapabilities.AnalogOutputCapabilities]
            ANALOG_OUTPUT_NONE: _ClassVar[ClientIdentification.ClientCapabilities.AnalogOutputCapabilities]
            ANALOG_OUTPUT_SUPPORTED: _ClassVar[ClientIdentification.ClientCapabilities.AnalogOutputCapabilities]
            ANALOG_OUTPUT_SUPPORTS_CGMS_A: _ClassVar[ClientIdentification.ClientCapabilities.AnalogOutputCapabilities]
        ANALOG_OUTPUT_UNKNOWN: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_NONE: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_SUPPORTED: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        ANALOG_OUTPUT_SUPPORTS_CGMS_A: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
        SESSION_TOKEN_FIELD_NUMBER: _ClassVar[int]
        VIDEO_RESOLUTION_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
        MAX_HDCP_VERSION_FIELD_NUMBER: _ClassVar[int]
        OEM_CRYPTO_API_VERSION_FIELD_NUMBER: _ClassVar[int]
        ANTI_ROLLBACK_USAGE_TABLE_FIELD_NUMBER: _ClassVar[int]
        SRM_VERSION_FIELD_NUMBER: _ClassVar[int]
        CAN_UPDATE_SRM_FIELD_NUMBER: _ClassVar[int]
        SUPPORTED_CERTIFICATE_KEY_TYPE_FIELD_NUMBER: _ClassVar[int]
        ANALOG_OUTPUT_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
        CAN_DISABLE_ANALOG_OUTPUT_FIELD_NUMBER: _ClassVar[int]
        RESOURCE_RATING_TIER_FIELD_NUMBER: _ClassVar[int]
        client_token: bool
        session_token: bool
        video_resolution_constraints: bool
        max_hdcp_version: ClientIdentification.ClientCapabilities.HdcpVersion
        oem_crypto_api_version: int
        anti_rollback_usage_table: bool
        srm_version: int
        can_update_srm: bool
        supported_certificate_key_type: _containers.RepeatedScalarFieldContainer[ClientIdentification.ClientCapabilities.CertificateKeyType]
        analog_output_capabilities: ClientIdentification.ClientCapabilities.AnalogOutputCapabilities
        can_disable_analog_output: bool
        resource_rating_tier: int
        def __init__(self, client_token: bool = ..., session_token: bool = ..., video_resolution_constraints: bool = ..., max_hdcp_version: _Optional[_Union[ClientIdentification.ClientCapabilities.HdcpVersion, str]] = ..., oem_crypto_api_version: _Optional[int] = ..., anti_rollback_usage_table: bool = ..., srm_version: _Optional[int] = ..., can_update_srm: bool = ..., supported_certificate_key_type: _Optional[_Iterable[_Union[ClientIdentification.ClientCapabilities.CertificateKeyType, str]]] = ..., analog_output_capabilities: _Optional[_Union[ClientIdentification.ClientCapabilities.AnalogOutputCapabilities, str]] = ..., can_disable_analog_output: bool = ..., resource_rating_tier: _Optional[int] = ...) -> None: ...
    class ClientCredentials(_message.Message):
        __slots__ = ("type", "token")
        TYPE_FIELD_NUMBER: _ClassVar[int]
        TOKEN_FIELD_NUMBER: _ClassVar[int]
        type: ClientIdentification.TokenType
        token: bytes
        def __init__(self, type: _Optional[_Union[ClientIdentification.TokenType, str]] = ..., token: _Optional[bytes] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    CLIENT_INFO_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_CLIENT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    LICENSE_COUNTER_FIELD_NUMBER: _ClassVar[int]
    CLIENT_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    VMP_DATA_FIELD_NUMBER: _ClassVar[int]
    DEVICE_CREDENTIALS_FIELD_NUMBER: _ClassVar[int]
    type: ClientIdentification.TokenType
    token: bytes
    client_info: _containers.RepeatedCompositeFieldContainer[ClientIdentification.NameValue]
    provider_client_token: bytes
    license_counter: int
    client_capabilities: ClientIdentification.ClientCapabilities
    vmp_data: bytes
    device_credentials: _containers.RepeatedCompositeFieldContainer[ClientIdentification.ClientCredentials]
    def __init__(self, type: _Optional[_Union[ClientIdentification.TokenType, str]] = ..., token: _Optional[bytes] = ..., client_info: _Optional[_Iterable[_Union[ClientIdentification.NameValue, _Mapping]]] = ..., provider_client_token: _Optional[bytes] = ..., license_counter: _Optional[int] = ..., client_capabilities: _Optional[_Union[ClientIdentification.ClientCapabilities, _Mapping]] = ..., vmp_data: _Optional[bytes] = ..., device_credentials: _Optional[_Iterable[_Union[ClientIdentification.ClientCredentials, _Mapping]]] = ...) -> None: ...

class EncryptedClientIdentification(_message.Message):
    __slots__ = ("provider_id", "service_certificate_serial_number", "encrypted_client_id", "encrypted_client_id_iv", "encrypted_privacy_key")
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_CERTIFICATE_SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_CLIENT_ID_IV_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTED_PRIVACY_KEY_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    service_certificate_serial_number: bytes
    encrypted_client_id: bytes
    encrypted_client_id_iv: bytes
    encrypted_privacy_key: bytes
    def __init__(self, provider_id: _Optional[str] = ..., service_certificate_serial_number: _Optional[bytes] = ..., encrypted_client_id: _Optional[bytes] = ..., encrypted_client_id_iv: _Optional[bytes] = ..., encrypted_privacy_key: _Optional[bytes] = ...) -> None: ...

class DrmCertificate(_message.Message):
    __slots__ = ("type", "serial_number", "creation_time_seconds", "expiration_time_seconds", "public_key", "system_id", "test_device_deprecated", "provider_id", "service_types", "algorithm", "rot_id", "encryption_key")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ROOT: _ClassVar[DrmCertificate.Type]
        DEVICE_MODEL: _ClassVar[DrmCertificate.Type]
        DEVICE: _ClassVar[DrmCertificate.Type]
        SERVICE: _ClassVar[DrmCertificate.Type]
        PROVISIONER: _ClassVar[DrmCertificate.Type]
    ROOT: DrmCertificate.Type
    DEVICE_MODEL: DrmCertificate.Type
    DEVICE: DrmCertificate.Type
    SERVICE: DrmCertificate.Type
    PROVISIONER: DrmCertificate.Type
    class ServiceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN_SERVICE_TYPE: _ClassVar[DrmCertificate.ServiceType]
        LICENSE_SERVER_SDK: _ClassVar[DrmCertificate.ServiceType]
        LICENSE_SERVER_PROXY_SDK: _ClassVar[DrmCertificate.ServiceType]
        PROVISIONING_SDK: _ClassVar[DrmCertificate.ServiceType]
        CAS_PROXY_SDK: _ClassVar[DrmCertificate.ServiceType]
    UNKNOWN_SERVICE_TYPE: DrmCertificate.ServiceType
    LICENSE_SERVER_SDK: DrmCertificate.ServiceType
    LICENSE_SERVER_PROXY_SDK: DrmCertificate.ServiceType
    PROVISIONING_SDK: DrmCertificate.ServiceType
    CAS_PROXY_SDK: DrmCertificate.ServiceType
    class Algorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN_ALGORITHM: _ClassVar[DrmCertificate.Algorithm]
        RSA: _ClassVar[DrmCertificate.Algorithm]
        ECC_SECP256R1: _ClassVar[DrmCertificate.Algorithm]
        ECC_SECP384R1: _ClassVar[DrmCertificate.Algorithm]
        ECC_SECP521R1: _ClassVar[DrmCertificate.Algorithm]
    UNKNOWN_ALGORITHM: DrmCertificate.Algorithm
    RSA: DrmCertificate.Algorithm
    ECC_SECP256R1: DrmCertificate.Algorithm
    ECC_SECP384R1: DrmCertificate.Algorithm
    ECC_SECP521R1: DrmCertificate.Algorithm
    class EncryptionKey(_message.Message):
        __slots__ = ("public_key", "algorithm")
        PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
        ALGORITHM_FIELD_NUMBER: _ClassVar[int]
        public_key: bytes
        algorithm: DrmCertificate.Algorithm
        def __init__(self, public_key: _Optional[bytes] = ..., algorithm: _Optional[_Union[DrmCertificate.Algorithm, str]] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    EXPIRATION_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_ID_FIELD_NUMBER: _ClassVar[int]
    TEST_DEVICE_DEPRECATED_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_TYPES_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    ROT_ID_FIELD_NUMBER: _ClassVar[int]
    ENCRYPTION_KEY_FIELD_NUMBER: _ClassVar[int]
    type: DrmCertificate.Type
    serial_number: bytes
    creation_time_seconds: int
    expiration_time_seconds: int
    public_key: bytes
    system_id: int
    test_device_deprecated: bool
    provider_id: str
    service_types: _containers.RepeatedScalarFieldContainer[DrmCertificate.ServiceType]
    algorithm: DrmCertificate.Algorithm
    rot_id: bytes
    encryption_key: DrmCertificate.EncryptionKey
    def __init__(self, type: _Optional[_Union[DrmCertificate.Type, str]] = ..., serial_number: _Optional[bytes] = ..., creation_time_seconds: _Optional[int] = ..., expiration_time_seconds: _Optional[int] = ..., public_key: _Optional[bytes] = ..., system_id: _Optional[int] = ..., test_device_deprecated: bool = ..., provider_id: _Optional[str] = ..., service_types: _Optional[_Iterable[_Union[DrmCertificate.ServiceType, str]]] = ..., algorithm: _Optional[_Union[DrmCertificate.Algorithm, str]] = ..., rot_id: _Optional[bytes] = ..., encryption_key: _Optional[_Union[DrmCertificate.EncryptionKey, _Mapping]] = ...) -> None: ...

class SignedDrmCertificate(_message.Message):
    __slots__ = ("drm_certificate", "signature", "signer", "hash_algorithm")
    DRM_CERTIFICATE_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    SIGNER_FIELD_NUMBER: _ClassVar[int]
    HASH_ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    drm_certificate: bytes
    signature: bytes
    signer: SignedDrmCertificate
    hash_algorithm: HashAlgorithmProto
    def __init__(self, drm_certificate: _Optional[bytes] = ..., signature: _Optional[bytes] = ..., signer: _Optional[_Union[SignedDrmCertificate, _Mapping]] = ..., hash_algorithm: _Optional[_Union[HashAlgorithmProto, str]] = ...) -> None: ...

class WidevinePsshData(_message.Message):
    __slots__ = ("key_ids", "content_id", "crypto_period_index", "protection_scheme", "crypto_period_seconds", "type", "key_sequence", "group_ids", "entitled_keys", "video_feature", "algorithm", "provider", "track_type", "policy", "grouped_license")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SINGLE: _ClassVar[WidevinePsshData.Type]
        ENTITLEMENT: _ClassVar[WidevinePsshData.Type]
        ENTITLED_KEY: _ClassVar[WidevinePsshData.Type]
    SINGLE: WidevinePsshData.Type
    ENTITLEMENT: WidevinePsshData.Type
    ENTITLED_KEY: WidevinePsshData.Type
    class Algorithm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNENCRYPTED: _ClassVar[WidevinePsshData.Algorithm]
        AESCTR: _ClassVar[WidevinePsshData.Algorithm]
    UNENCRYPTED: WidevinePsshData.Algorithm
    AESCTR: WidevinePsshData.Algorithm
    class EntitledKey(_message.Message):
        __slots__ = ("entitlement_key_id", "key_id", "key", "iv", "entitlement_key_size_bytes")
        ENTITLEMENT_KEY_ID_FIELD_NUMBER: _ClassVar[int]
        KEY_ID_FIELD_NUMBER: _ClassVar[int]
        KEY_FIELD_NUMBER: _ClassVar[int]
        IV_FIELD_NUMBER: _ClassVar[int]
        ENTITLEMENT_KEY_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
        entitlement_key_id: bytes
        key_id: bytes
        key: bytes
        iv: bytes
        entitlement_key_size_bytes: int
        def __init__(self, entitlement_key_id: _Optional[bytes] = ..., key_id: _Optional[bytes] = ..., key: _Optional[bytes] = ..., iv: _Optional[bytes] = ..., entitlement_key_size_bytes: _Optional[int] = ...) -> None: ...
    KEY_IDS_FIELD_NUMBER: _ClassVar[int]
    CONTENT_ID_FIELD_NUMBER: _ClassVar[int]
    CRYPTO_PERIOD_INDEX_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_SCHEME_FIELD_NUMBER: _ClassVar[int]
    CRYPTO_PERIOD_SECONDS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    ENTITLED_KEYS_FIELD_NUMBER: _ClassVar[int]
    VIDEO_FEATURE_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    TRACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    GROUPED_LICENSE_FIELD_NUMBER: _ClassVar[int]
    key_ids: _containers.RepeatedScalarFieldContainer[bytes]
    content_id: bytes
    crypto_period_index: int
    protection_scheme: int
    crypto_period_seconds: int
    type: WidevinePsshData.Type
    key_sequence: int
    group_ids: _containers.RepeatedScalarFieldContainer[bytes]
    entitled_keys: _containers.RepeatedCompositeFieldContainer[WidevinePsshData.EntitledKey]
    video_feature: str
    algorithm: WidevinePsshData.Algorithm
    provider: str
    track_type: str
    policy: str
    grouped_license: bytes
    def __init__(self, key_ids: _Optional[_Iterable[bytes]] = ..., content_id: _Optional[bytes] = ..., crypto_period_index: _Optional[int] = ..., protection_scheme: _Optional[int] = ..., crypto_period_seconds: _Optional[int] = ..., type: _Optional[_Union[WidevinePsshData.Type, str]] = ..., key_sequence: _Optional[int] = ..., group_ids: _Optional[_Iterable[bytes]] = ..., entitled_keys: _Optional[_Iterable[_Union[WidevinePsshData.EntitledKey, _Mapping]]] = ..., video_feature: _Optional[str] = ..., algorithm: _Optional[_Union[WidevinePsshData.Algorithm, str]] = ..., provider: _Optional[str] = ..., track_type: _Optional[str] = ..., policy: _Optional[str] = ..., grouped_license: _Optional[bytes] = ...) -> None: ...

class VmpData(_message.Message):
    __slots__ = ("certificates", "signed_binary_info", "cdm_host_files", "cdm_call_chain_files", "current_process_file", "host_file_indexes", "call_chain_file_indexes", "current_process_file_index")
    class SignedBinaryInfo(_message.Message):
        __slots__ = ("file_name", "certificate_index", "binary_hash", "flags", "signature", "hash_algorithm")
        class HashAlgorithmProto(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            HASH_ALGORITHM_UNSPECIFIED: _ClassVar[VmpData.SignedBinaryInfo.HashAlgorithmProto]
            HASH_ALGORITHM_SHA_1: _ClassVar[VmpData.SignedBinaryInfo.HashAlgorithmProto]
            HASH_ALGORITHM_SHA_256: _ClassVar[VmpData.SignedBinaryInfo.HashAlgorithmProto]
            HASH_ALGORITHM_SHA_384: _ClassVar[VmpData.SignedBinaryInfo.HashAlgorithmProto]
        HASH_ALGORITHM_UNSPECIFIED: VmpData.SignedBinaryInfo.HashAlgorithmProto
        HASH_ALGORITHM_SHA_1: VmpData.SignedBinaryInfo.HashAlgorithmProto
        HASH_ALGORITHM_SHA_256: VmpData.SignedBinaryInfo.HashAlgorithmProto
        HASH_ALGORITHM_SHA_384: VmpData.SignedBinaryInfo.HashAlgorithmProto
        FILE_NAME_FIELD_NUMBER: _ClassVar[int]
        CERTIFICATE_INDEX_FIELD_NUMBER: _ClassVar[int]
        BINARY_HASH_FIELD_NUMBER: _ClassVar[int]
        FLAGS_FIELD_NUMBER: _ClassVar[int]
        SIGNATURE_FIELD_NUMBER: _ClassVar[int]
        HASH_ALGORITHM_FIELD_NUMBER: _ClassVar[int]
        file_name: str
        certificate_index: int
        binary_hash: bytes
        flags: int
        signature: bytes
        hash_algorithm: VmpData.SignedBinaryInfo.HashAlgorithmProto
        def __init__(self, file_name: _Optional[str] = ..., certificate_index: _Optional[int] = ..., binary_hash: _Optional[bytes] = ..., flags: _Optional[int] = ..., signature: _Optional[bytes] = ..., hash_algorithm: _Optional[_Union[VmpData.SignedBinaryInfo.HashAlgorithmProto, str]] = ...) -> None: ...
    CERTIFICATES_FIELD_NUMBER: _ClassVar[int]
    SIGNED_BINARY_INFO_FIELD_NUMBER: _ClassVar[int]
    CDM_HOST_FILES_FIELD_NUMBER: _ClassVar[int]
    CDM_CALL_CHAIN_FILES_FIELD_NUMBER: _ClassVar[int]
    CURRENT_PROCESS_FILE_FIELD_NUMBER: _ClassVar[int]
    HOST_FILE_INDEXES_FIELD_NUMBER: _ClassVar[int]
    CALL_CHAIN_FILE_INDEXES_FIELD_NUMBER: _ClassVar[int]
    CURRENT_PROCESS_FILE_INDEX_FIELD_NUMBER: _ClassVar[int]
    certificates: _containers.RepeatedScalarFieldContainer[bytes]
    signed_binary_info: _containers.RepeatedCompositeFieldContainer[VmpData.SignedBinaryInfo]
    cdm_host_files: _containers.RepeatedCompositeFieldContainer[VmpData.SignedBinaryInfo]
    cdm_call_chain_files: _containers.RepeatedCompositeFieldContainer[VmpData.SignedBinaryInfo]
    current_process_file: VmpData.SignedBinaryInfo
    host_file_indexes: _containers.RepeatedScalarFieldContainer[int]
    call_chain_file_indexes: _containers.RepeatedScalarFieldContainer[int]
    current_process_file_index: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, certificates: _Optional[_Iterable[bytes]] = ..., signed_binary_info: _Optional[_Iterable[_Union[VmpData.SignedBinaryInfo, _Mapping]]] = ..., cdm_host_files: _Optional[_Iterable[_Union[VmpData.SignedBinaryInfo, _Mapping]]] = ..., cdm_call_chain_files: _Optional[_Iterable[_Union[VmpData.SignedBinaryInfo, _Mapping]]] = ..., current_process_file: _Optional[_Union[VmpData.SignedBinaryInfo, _Mapping]] = ..., host_file_indexes: _Optional[_Iterable[int]] = ..., call_chain_file_indexes: _Optional[_Iterable[int]] = ..., current_process_file_index: _Optional[_Iterable[int]] = ...) -> None: ...
