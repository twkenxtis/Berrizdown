import asyncio
from functools import cached_property
from typing import Any

from httpx import Response
from lib.__init__ import use_proxy
from lib.download.download import Start_Download_Queue
from lib.mux.parse_m3u8 import rebuild_master_playlist
from static.api_error_handle import api_error_handle
from static.color import Color
from static.parameter import paramstore
from static.PlaybackInfo import LivePlaybackInfo, PlaybackInfo
from static.PublicInfo import PublicInfo
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import Live, Playback_info, Public_context
from unit.media.console_print import print_title
from unit.media.drm_typing_dict import LivePlaybackResponse, PlaybackResponse, PublicResponse, SelectedMedia, SelectedMediaItem
from unit.media.keyhandle import Key_handle

logger = setup_logging("drm", "tomato")


async def start_download(
    public_info: PublicInfo,
    playback_info: PlaybackInfo,
    decryption_key: list[str],
    raw_mpd: Any,
    raw_hls: str,
    input_community_name: str,
) -> None:
    if playback_info.code != "0000":
        logger.info("Skip download video")
    elif paramstore.get("key") is True:
        pass
    else:
        if (playback_info.dash_playback_url and playback_info.hls_playback_url.startswith("http")) or (playback_info.dash_playback_url and playback_info.hls_playback_url.startswith("http")):
            await Start_Download_Queue(
                decryption_key,
                public_info,
                playback_info,
                raw_mpd,
                raw_hls,
                input_community_name,
            ).run_dl()


class BerrizProcessor:
    def __init__(
        self,
        media_id: str,
        media_type: str,
        selected_media: SelectedMedia,
        input_community_name: str,
    ):
        self.media_id: str = media_id
        self.media_type: str = media_type
        self.selected_media: SelectedMedia = selected_media
        self.input_community_name: str = input_community_name

    @cached_property
    def Live(self) -> Live:
        return Live()

    @cached_property
    def Playback_info(self) -> Playback_info:
        return Playback_info()

    @cached_property
    def Public_context(self) -> Public_context:
        return Public_context()

    def _log_skipped_media(self, media_item: SelectedMediaItem) -> None:
        """Log information about skipped media when no cookie is available."""
        logger.info(
            f"{Color.bg('ruby')}Skip video because without cookie:{Color.reset()}{Color.fg('light_magenta')} {media_item['title']}{Color.reset()}",
        )
        logger.info(
            f"{Color.fg('beige')}Mediatype: {media_item['mediaType']}{Color.reset()} "
            f"{Color.fg('tan')}[{media_item['mediaId']}]{Color.reset()} "
            f"{Color.fg('peach')}{media_item['thumbnailUrl']}{Color.reset()} "
            f"{Color.fg('teal')}isFanclubOnly:{media_item['isFanclubOnly']}{Color.reset()}"
        )

    def _handle_no_cookie_scenario(self) -> tuple[None, None]:
        """Handle the case when no cookie is available."""
        selected_media_list: list[SelectedMediaItem] | None = None

        if self.selected_media.get("lives") is not None:
            selected_media_list = self.selected_media.get("lives")
        elif self.selected_media.get("vods") is not None:
            selected_media_list = self.selected_media.get("vods")

        if selected_media_list:
            for media_item in selected_media_list:
                self._log_skipped_media(media_item)

        return None, None

    async def _fetch_vod_contexts(
        self,
    ) -> tuple[list[PlaybackResponse] | None, list[PublicResponse] | None]:
        """Fetch playback and public contexts for VOD media."""
        playback, public = await asyncio.gather(
            self.Playback_info.get_playback_context(self.media_id, use_proxy),
            self.Public_context.get_public_context(self.media_id, use_proxy),
        )
        if playback and playback[0].get("code") == "0000":
            return playback, public
        return None, public

    async def _fetch_live_contexts(
        self,
    ) -> tuple[list[LivePlaybackResponse] | None, list[PublicResponse] | None]:
        """Fetch playback and public contexts for LIVE media."""
        playback = await self.Playback_info.get_live_playback_info(self.media_id, use_proxy)
        public = await self.Public_context.get_public_context(self.media_id, use_proxy)

        if playback and playback[0].get("code") == "0000":
            return playback, public
        return None, public

    async def fetch_contexts(
        self,
    ) -> tuple[
        list[PlaybackResponse | LivePlaybackResponse] | None,
        list[PublicResponse] | None,
    ]:
        if paramstore.get("no_cookie"):
            return self._handle_no_cookie_scenario()

        if self.media_type == "VOD":
            return await self._fetch_vod_contexts()
        elif self.media_type == "LIVE":
            return await self._fetch_live_contexts()

        return None, None

    async def prepare_download_tasks(
        self,
        playback: list[PlaybackResponse | LivePlaybackResponse] | None,
        public: list[PublicResponse] | None,
    ) -> bool | None:
        """Prepare and execute download tasks for the fetched media"""
        if playback is None:
            if public:
                for response in public:
                    title = response.get("data", {}).get("media", {}).get("title", "")
                    logger.warning(f"Skip {Color.fg('sunflower')}{title}{Color.reset()}")
            return False

        if not playback:
            return False

        playback_ctx = playback[0]
        public_ctx = public[0] if public else None

        if not public_ctx:
            return False

        if self.media_type == "VOD":
            playback_info, public_info = await asyncio.gather(
                asyncio.to_thread(PlaybackInfo, playback_ctx),
                asyncio.to_thread(PublicInfo, public_ctx),
            )
        elif self.media_type == "LIVE":
            playback_info, public_info = await asyncio.gather(
                asyncio.to_thread(LivePlaybackInfo, playback_ctx),
                asyncio.to_thread(PublicInfo, public_ctx),
            )
        else:
            return False

        return await self.pre_make_download(playback_info, public_info)

    async def pre_make_download(self, playback_info: PlaybackInfo | LivePlaybackInfo, public_info: PublicInfo) -> None:
        """Prepare download by handling DRM and fetching manifest files"""
        logger.debug(playback_info.to_dict())
        logger.debug(public_info.to_dict())

        key, raw_hls, raw_mpd = await self.drm_handle(playback_info, public_info)

        if not any(not v for v in (raw_hls, raw_mpd)):
            await start_download(
                public_info,
                playback_info,
                key,
                raw_mpd,
                raw_hls,
                self.input_community_name,
            )
        else:
            missing = {
                "raw_mpd": raw_mpd,
                "raw_hls": raw_hls,
            }
            for name, value in missing.items():
                if not value:
                    logger.warning(f"Missing or invalid: {name} = {repr(value)}")

    async def drm_handle(self, playback_info: PlaybackInfo | LivePlaybackInfo, public_info: PublicInfo) -> tuple[list[str] | None, str | None, Response | None]:
        if playback_info.code != "0000":
            logger.warning(f"{Color.bg('maroon')}{api_error_handle(playback_info.code)}{Color.reset()}")
            return None, None, None

        raw_mpd: Response | None = None
        raw_hls: str | None = None

        if getattr(playback_info, "dash_playback_url", None):
            raw_mpd = await self.Live.fetch_mpd(playback_info.dash_playback_url, use_proxy)

        if getattr(playback_info, "hls_playback_url", None):
            response_hls = await self.Live.fetch_mpd(playback_info.hls_playback_url, use_proxy)
            raw_hls = await rebuild_master_playlist(response_hls, playback_info.hls_playback_url)

        key: list[str] | None = None

        if getattr(playback_info, "is_drm", None) is True:
            key_handler = Key_handle(playback_info, self.media_id, raw_mpd)
            pk = await key_handler.send_drm()
            if pk:
                key_list, media_id_from_drm = pk
                key = key_list
            print_title(public_info, playback_info, key_handler, key)
        elif getattr(playback_info, "is_drm", None) is False:
            print_title(public_info, playback_info)
        else:
            logger.error(f"Invalid DRM status for media ID: {self.media_id}")
            raise Exception(f"Check {getattr(playback_info, 'dash_playback_url', None)} PSSH or DRM info!")

        return key, raw_hls, raw_mpd

    async def run(self) -> None:
        """Main entry point to run the processor"""
        playback, public = await self.fetch_contexts()
        if playback is not None:
            await self.prepare_download_tasks(playback, public)
        else:
            if public:
                logger.error(f"Playback is null{Color.reset()} {Color.fg('ruby')}{PublicInfo(public[0]).__str__()}{Color.reset()}")
            print("")
