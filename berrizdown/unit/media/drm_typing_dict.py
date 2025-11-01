from typing import Literal, NotRequired, TypedDict


class FairplayDrmInfo(TypedDict):
    licenseUrl: str
    certUrl: str


class WidevineDrmInfo(TypedDict):
    licenseUrl: str


class PlayreadyDrmInfo(TypedDict):
    licenseUrl: str


class DrmInfo(TypedDict):
    assertion: str
    widevine: WidevineDrmInfo
    playready: PlayreadyDrmInfo
    fairplay: FairplayDrmInfo


# HLS/DASH Related TypedDicts
class AdaptationSet(TypedDict):
    width: int
    height: int
    playbackUrl: str


class HlsInfo(TypedDict):
    playbackUrl: str
    adaptationSet: list[AdaptationSet]


class DashInfo(TypedDict):
    playbackUrl: str


# VOD Related TypedDicts
class VodData(TypedDict):
    duration: int
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    isDrm: bool
    drmInfo: DrmInfo
    hls: HlsInfo
    dash: DashInfo
    videoRatingAssessmentId: str | None


# Tracking and Settlement TypedDicts
class TrackingInfo(TypedDict):
    trackingPlaybackPollingIntervalSec: int


class SettlementInfo(TypedDict):
    mediaSettlementToken: str


# Playback Response TypedDict
class PlaybackData(TypedDict):
    vod: NotRequired[VodData]
    photo: dict | None
    youtube: dict | None
    tracking: TrackingInfo
    settlement: SettlementInfo
    videoRatingAssessment: dict | None


class PlaybackResponse(TypedDict):
    code: str
    message: str
    data: PlaybackData


# Media Related TypedDicts
class MediaInfo(TypedDict):
    mediaSeq: int
    mediaId: str
    mediaType: Literal["VOD", "LIVE", "PHOTO"]
    title: str
    body: str
    thumbnailUrl: str
    publishedAt: str
    communityId: int
    isFanclubOnly: bool
    videoRatingAssessmentId: str | None


class CommunityArtist(TypedDict):
    communityArtistId: int
    name: str
    imageUrl: str


class MediaCategory(TypedDict):
    mediaCategoryId: int
    mediaCategoryName: str


class CommentInfo(TypedDict):
    contentTypeCode: str
    readContentId: str
    writeContentId: str


# Public Context Response TypedDict
class PublicData(TypedDict):
    media: MediaInfo
    communityArtists: list[CommunityArtist]
    mediaCategories: list[MediaCategory]
    comment: CommentInfo
    videoRatingAssessment: dict | None


class PublicResponse(TypedDict):
    code: str
    message: str
    data: PublicData


# Selected Media TypedDict [for userchoice input]
class SelectedMediaItem(TypedDict):
    title: str
    mediaType: Literal["VOD", "LIVE", "PHOTO"]
    mediaId: str
    thumbnailUrl: str
    isFanclubOnly: bool


class SelectedMedia(TypedDict):
    vods: NotRequired[list[SelectedMediaItem]]
    lives: NotRequired[list[SelectedMediaItem]]


# Live Playback TypedDicts
class LiveVodData(TypedDict):
    duration: NotRequired[int]
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    isDrm: bool
    drmInfo: NotRequired[DrmInfo]
    hls: HlsInfo
    dash: NotRequired[DashInfo]
    videoRatingAssessmentId: str | None


class LivePlaybackData(TypedDict):
    vod: NotRequired[LiveVodData]
    tracking: TrackingInfo
    settlement: SettlementInfo
    videoRatingAssessment: dict | None


class LivePlaybackResponse(TypedDict):
    code: str
    message: str
    data: LivePlaybackData


# DRM Key Result TypedDict
class DrmKeyResult(TypedDict):
    key_list: list[str]
    media_id: str
