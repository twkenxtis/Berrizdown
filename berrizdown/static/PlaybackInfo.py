import warnings
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


class WidevineInfo(BaseModel):
    license_url: str | None = Field(None, alias="licenseUrl")


class PlayreadyInfo(BaseModel):
    license_url: str | None = Field(None, alias="licenseUrl")


class FairplayInfo(BaseModel):
    license_url: str | None = Field(None, alias="licenseUrl")
    cert_url: str | None = Field(None, alias="certUrl")


class DRMInfo(BaseModel):
    """DRM"""

    assertion: str | None = None
    widevine: WidevineInfo | None = Field(None)
    playready: PlayreadyInfo | None = Field(None)
    fairplay: FairplayInfo | None = Field(None)


class HLSAdaptation(BaseModel):
    # 用於 PlaybackInfo.hls_adaptations
    mime_type: str | None = Field(None, alias="mimeType")
    width: int | None = None
    height: int | None = None
    bitrate: int | None = None
    codecs: str | None = None


class HLSData(BaseModel):
    playback_url: str | None = Field(None, alias="playbackUrl")
    adaptation_set: list[HLSAdaptation] = Field(default_factory=list, alias="adaptationSet")


class DASHData(BaseModel):
    playback_url: str | None = Field(None, alias="playbackUrl")


class VODData(BaseModel):
    duration: int | None = None
    orientation: str | None = None
    is_drm: bool | None = Field(None, alias="isDrm")
    drm_info: DRMInfo | None = Field(None, alias="drmInfo")
    hls: HLSData = Field(default_factory=HLSData)
    dash: DASHData = Field(default_factory=DASHData)


class TrackingData(BaseModel):
    tracking_playback_polling_interval_sec: int | None = Field(None, alias="trackingPlaybackPollingIntervalSec")


class SettlementData(BaseModel):
    media_settlement_token: str | None = Field(None, alias="mediaSettlementToken")


class PlaybackData(BaseModel):
    vod: VODData = Field(default_factory=VODData)
    tracking: TrackingData = Field(default_factory=TrackingData)
    settlement: SettlementData = Field(default_factory=SettlementData)


class PlaybackPayload(BaseModel):
    """VOD API"""

    code: str | None = None
    message: str | None = None
    data: PlaybackData = Field(default_factory=PlaybackData)


# --- PlaybackInfo 類別 (VOD) ---


class PlaybackInfo:
    code: str | None
    status: str | None
    duration: int | None
    orientation: str | None
    is_drm: bool | None
    drm_info: dict[str, Any]
    assertion: str | None
    widevine_license: str | None
    playready_license: str | None
    fairplay_license: str | None
    fairplay_cert: str | None
    hls_playback_url: str | None
    hls_adaptations: list[dict[str, Any]]
    dash_playback_url: str | None
    tracking_interval: int | None
    settlement_token: str | None

    def __init__(self, playback_context: dict[str, Any] | tuple[Any, dict[str, Any]]):
        if isinstance(playback_context, tuple):
            context_data = playback_context[1]
        else:
            context_data = playback_context

        validated: PlaybackPayload = PlaybackPayload.model_validate(context_data)

        self.code = validated.code
        self.status = validated.message

        # VOD data
        vod_data = validated.data.vod
        self.duration = vod_data.duration
        self.orientation = vod_data.orientation
        self.is_drm = vod_data.is_drm

        # DRM info
        drm_info = vod_data.drm_info
        self.drm_info: dict[str, Any] = drm_info.model_dump(by_alias=True) if drm_info else {}

        if drm_info and drm_info.assertion:
            self.assertion = drm_info.assertion

            self.widevine_license = drm_info.widevine.license_url if drm_info.widevine else ""

            self.playready_license = drm_info.playready.license_url if drm_info.playready else ""

            self.fairplay_license = drm_info.fairplay.license_url if drm_info.fairplay else ""
            self.fairplay_cert = drm_info.fairplay.cert_url if drm_info.fairplay else ""
        else:
            # if no drm info, set empty values
            self.assertion = ""
            self.widevine_license = ""
            self.playready_license = ""
            self.fairplay_license = ""
            self.fairplay_cert = ""

        # HLS data
        hls_data = vod_data.hls
        self.hls_playback_url = hls_data.playback_url

        self.hls_adaptations: list[dict[str, Any]] = [item.model_dump(by_alias=True) for item in hls_data.adaptation_set]

        # DASH data
        self.dash_playback_url = vod_data.dash.playback_url

        # Tracking info
        self.tracking_interval = validated.data.tracking.tracking_playback_polling_interval_sec

        # Settlement info
        self.settlement_token = validated.data.settlement.media_settlement_token

    def to_dict(self) -> dict[str, Any]:
        """Convert all data to dictionary"""
        if self.code != "0000":
            return {"error": "Invalid status code"}

        return {
            "code": self.code,
            "status": self.status,
            "vod": {
                "duration": self.duration,
                "orientation": self.orientation,
                "is_drm": self.is_drm,
                "drm_info": {
                    "assertion": getattr(self, "assertion", ""),
                    "widevine_license": getattr(self, "widevine_license", ""),
                    "playready_license": getattr(self, "playready_license", ""),
                    "fairplay": {
                        "license": getattr(self, "fairplay_license", ""),
                        "cert": getattr(self, "fairplay_cert", ""),
                    },
                },
                "hls": {
                    "playback_url": self.hls_playback_url,
                    "adaptations": self.hls_adaptations,
                },
                "dash": {
                    "playback_url": self.dash_playback_url,
                },
            },
            "tracking_interval": self.tracking_interval,
            "settlement_token": self.settlement_token,
        }

    def to_json(self) -> str:
        """Convert to JSON string with pretty formatting"""
        return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2).decode("utf-8")

    def __str__(self) -> str:
        """String representation of the object"""
        return f"PlaybackInfo(code={self.code}, status={self.status}, duration={self.duration})"


class MediaInfo(BaseModel):
    media_seq: int | None = Field(None, alias="mediaSeq")
    media_id: UUID | None = Field(None, alias="mediaId")
    media_type: str | None = Field(None, alias="mediaType")
    title: str | None = None
    thumbnail_url: str | None = Field(None, alias="thumbnailUrl")
    published_at: str | None = Field(None, alias="publishedAt")
    community_id: int | None = Field(None, alias="communityId")
    is_fanclub_only: bool | None = Field(None, alias="isFanclubOnly")

    live_status: str | None = Field(None, alias="liveStatus")  # this only in Live


class ReplayHLSAdaptation(BaseModel):
    # LivePlaybackInfo.hls_adaptation_set
    width: int | None = None
    height: int | None = None
    playback_url: str | None = Field(None, alias="playbackUrl")


class ReplayHLSData(BaseModel):
    playback_url: str | None = Field(None, alias="playbackUrl")
    adaptation_set: list[ReplayHLSAdaptation] = Field(default_factory=list, alias="adaptationSet")


class ReplayData(BaseModel):
    """Live Replay API only in Live"""

    duration: int | None = None
    orientation: str | None = None
    is_drm: bool | None = Field(None, alias="isDrm")
    drm_info: DRMInfo | None = Field(None, alias="drmInfo")
    dash: DASHData = Field(default_factory=DASHData)
    hls: ReplayHLSData = Field(default_factory=ReplayHLSData)


class LiveInfo(BaseModel):
    live_status: str | None = Field(None, alias="liveStatus")
    replay: ReplayData = Field(default_factory=ReplayData)


class LiveMediaInfo(MediaInfo):
    live: LiveInfo = Field(default_factory=LiveInfo)


class CommunityArtist(BaseModel):
    community_artist_id: int | None = Field(None, alias="communityArtistId")
    name: str | None = None
    image_url: str | None = Field(None, alias="imageUrl")


class LivePlaybackData(BaseModel):
    media: LiveMediaInfo = Field(default_factory=LiveMediaInfo)
    community_artists: list[CommunityArtist] = Field(default_factory=list, alias="communityArtists")
    tracking: TrackingData = Field(default_factory=TrackingData)
    settlement: SettlementData = Field(default_factory=SettlementData)
    link: str | None = None
    video_rating_assessment: dict[str, Any] | None = Field(None, alias="videoRatingAssessment")


class LivePlaybackPayload(BaseModel):
    """Live Playback API / No media live only api"""

    code: str | None = None
    message: str | None = None
    data: LivePlaybackData = Field(default_factory=LivePlaybackData)


class LivePlaybackInfo:
    code: str | None
    status: str | None
    media_seq: int | None
    media_id: UUID | None
    media_type: str | None
    title: str | None
    thumbnail_url: str | None
    published_at: str | None
    community_id: int | None
    is_fanclub_only: bool | None
    live_status: str | None
    duration: int | None
    orientation: str | None
    is_drm: bool | None
    drm_info: dict[str, Any] | None
    dash_playback_url: str | None
    assertion: str | None
    widevine_license: str | None
    playready_license: str | None
    fairplay_license: str | None
    fairplay_cert: str | None
    hls_playback_url: str | None
    hls_adaptation_set: list[dict[str, Any]]
    community_artists: list[dict[str, Any]]
    tracking_interval_sec: int | None
    settlement_token: str | None
    link: str | None
    video_rating_assessment: dict[str, Any] | None

    def __init__(self, playback_context: dict[str, Any] | tuple[Any, dict[str, Any]]):
        if isinstance(playback_context, tuple):
            context_data = playback_context[1]
        else:
            context_data = playback_context

        validated: LivePlaybackPayload = LivePlaybackPayload.model_validate(context_data)

        # Top-level info
        self.code = validated.code
        self.status = validated.message

        data = validated.data
        media = data.media
        live = media.live
        replay = live.replay

        # Media info
        self.media_seq = media.media_seq
        self.media_id = media.media_id
        self.media_type = media.media_type
        self.title = media.title
        self.thumbnail_url = media.thumbnail_url
        self.published_at = media.published_at
        self.community_id = media.community_id
        self.is_fanclub_only = media.is_fanclub_only

        # Live replay info
        self.live_status = live.live_status
        self.duration = replay.duration
        self.orientation = replay.orientation
        self.is_drm = replay.is_drm

        # DRM & Playback
        drm_info = replay.drm_info
        self.drm_info: dict[str, Any] | None = drm_info.model_dump(by_alias=True) if drm_info else None

        # DASH playback
        self.dash_playback_url = replay.dash.playback_url

        # DRM
        if drm_info and drm_info.assertion:
            self.assertion = drm_info.assertion

            self.widevine_license = drm_info.widevine.license_url if drm_info.widevine else ""

            self.playready_license = drm_info.playready.license_url if drm_info.playready else ""

            self.fairplay_license = drm_info.fairplay.license_url if drm_info.fairplay else ""
            self.fairplay_cert = drm_info.fairplay.cert_url if drm_info.fairplay else ""
        else:
            self.assertion = ""
            self.widevine_license = ""
            self.playready_license = ""
            self.fairplay_license = ""
            self.fairplay_cert = ""

        # HLS playback
        hls_data = replay.hls
        self.hls_playback_url = hls_data.playback_url

        self.hls_adaptation_set: list[dict[str, Any]] = [
            {
                "width": stream.width,
                "height": stream.height,
                "playback_url": stream.playback_url,
            }
            for stream in hls_data.adaptation_set
        ]

        # Artist info
        self.community_artists: list[dict[str, Any]] = [
            {
                "id": artist.community_artist_id,
                "name": artist.name,
                "image_url": artist.image_url,
            }
            for artist in data.community_artists
        ]

        # Tracking
        self.tracking_interval_sec = data.tracking.tracking_playback_polling_interval_sec

        # Settlement
        self.settlement_token = data.settlement.media_settlement_token

        # External link
        self.link = data.link

        # Optional rating assessment
        self.video_rating_assessment = data.video_rating_assessment

    def to_dict(self) -> dict[str, Any]:
        """Convert all data to dictionary"""
        if self.code != "0000":
            return {"error": "Invalid status code"}

        return {
            "code": self.code,
            "status": self.status,
            "media": {
                "seq": self.media_seq,
                "id": self.media_id,
                "type": self.media_type,
                "title": self.title,
                "thumbnail_url": self.thumbnail_url,
                "published_at": self.published_at,
                "community_id": self.community_id,
                "is_fanclub_only": self.is_fanclub_only,
                "live": {
                    "status": self.live_status,
                    "replay": {
                        "duration": self.duration,
                        "orientation": self.orientation,
                        "is_drm": self.is_drm,
                        "drm_info": {
                            "assertion": getattr(self, "assertion", ""),
                            "widevine_license": getattr(self, "widevine_license", ""),
                            "playready_license": getattr(self, "playready_license", ""),
                            "fairplay": {
                                "license": getattr(self, "fairplay_license", ""),
                                "cert": getattr(self, "fairplay_cert", ""),
                            },
                        },
                        "dash": {
                            "playback_url": self.dash_playback_url,
                        },
                        "hls": {
                            "playback_url": self.hls_playback_url,
                            "adaptation_set": self.hls_adaptation_set,
                        },
                    },
                },
            },
            "community_artists": self.community_artists,
            "tracking_interval_sec": self.tracking_interval_sec,
            "settlement_token": self.settlement_token,
            "link": self.link,
            "video_rating_assessment": self.video_rating_assessment,
        }

    def to_json(self) -> str:
        """Convert to JSON string with pretty formatting"""
        return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2).decode("utf-8")

    def __str__(self) -> str:
        """String representation of the object"""
        return f"LivePlaybackInfo(media_id={self.media_id}, title={self.title}, live_status={self.live_status})"
