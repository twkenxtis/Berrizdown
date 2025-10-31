import asyncio
from functools import cached_property
from typing import Any

from key.GetClearKey import get_clear_key
from key.local_vault import SQLiteKeyVault
from key.msprpro import GetMPD_prd
from key.pssh import GetMPD_wv
from lib.load_yaml_config import CFG, ConfigLoader
from static.color import Color
from static.parameter import paramstore
from static.PlaybackInfo import PlaybackInfo
from unit.handle.handle_log import setup_logging

logger = setup_logging("keyhandle", "amber")


class Key_handle:
    def __init__(self, playback_info: PlaybackInfo, media_id: str, raw_mpd: Any):
        self._mspr_pro: list[str] | None = None
        self._wv_pssh: list[str] | None = None
        self.playback_info: PlaybackInfo = playback_info
        self.assertion: str | None = playback_info.assertion
        self.dash_playback_url: str | None = playback_info.dash_playback_url
        self.media_id: str = media_id
        self.raw_mpd: Any = raw_mpd

    @cached_property
    def drm_type(self) -> str:
        return self._normalize_drm_type(CFG["KeyService"]["source"])

    @cached_property
    def vault(self) -> SQLiteKeyVault:
        return SQLiteKeyVault()

    @property
    def mspr_pro(self) -> list[str] | None:
        if self._mspr_pro is None and self.raw_mpd:
            parsed = GetMPD_prd.parse_pssh(self.raw_mpd)
            self._mspr_pro = list(set(parsed))
        return self._mspr_pro

    @property
    def wv_pssh(self) -> list[str] | None:
        if self._wv_pssh is None and self.raw_mpd:
            parsed = GetMPD_wv.parse_pssh(self.raw_mpd)
            self._wv_pssh = list(set(parsed))
        return self._wv_pssh

    async def send_drm(self) -> tuple[list[str], str] | None:
        """主要的 DRM 處理流程"""
        if self.playback_info.code != "0000":
            logger.error(f"Error code: {self.playback_info.code}", self.playback_info)
            raise Exception(f"Invalid response code: {self.playback_info.code}")

        if not getattr(self.playback_info, "is_drm", False):
            return None
        # 先嘗試從快取找
        if not paramstore.get("no_cache_key"):
            key = await self.search_keys()
            if key:
                return [key], self.media_id
        # 再嘗試請求新 key
        if not paramstore.get("cache_key"):
            keys = await self.request_keys()
            return (list(keys), self.media_id) if keys else None
        logger.warning("No keys found in local vault")
        return None

    async def save_key(self, key: str) -> None:
        if not key:
            logger.error("Key is None. Cannot save to vault.")
            return

        async def _store_and_log(pssh: str, drm: str) -> None:
            await self.vault.store_single(pssh, key, drm)
            if self.vault.contains(pssh):
                logger.info(f"{Color.fg('iceberg')}SUCCESS save key to local vault:{Color.reset()} {Color.fg('iron')}{key}{Color.reset()} - {Color.fg('ruby')}{drm}{Color.reset()}")
            else:
                logger.error(f"Key verification FAILED for: {pssh}")

        jobs: list[asyncio.Task[Any]] = []
        if self.wv_pssh:
            jobs += [asyncio.create_task(_store_and_log(pssh, "widevine")) for pssh in self.wv_pssh]
        if self.mspr_pro:
            jobs += [asyncio.create_task(_store_and_log(pssh, "playready")) for pssh in self.mspr_pro]
        if jobs:
            await asyncio.gather(*jobs)

    async def search_keys(self) -> str | None:
        """從本地 Vault 搜尋 key"""
        wv, ms_pr = None, None
        if self.wv_pssh:
            for pssh in self.wv_pssh:
                wv = await self.vault.retrieve(pssh)
        if self.mspr_pro:
            for pssh in self.mspr_pro:
                ms_pr = await self.vault.retrieve(pssh)
        key = ms_pr or wv
        if key:
            kid, val = key.split(":")
            logger.info(f"{Color.fg('mint')}Use local key vault keys: {Color.reset()}{Color.fg('khaki')}kid:{Color.fg('gold')}{kid} {Color.fg('bright_red')}key:{Color.fg('gold')}{val}{Color.reset()}")
            return key
        return None

    async def request_keys(self) -> list[str] | None:
        """向伺服器請求新 key"""
        if not (self.wv_pssh and self.mspr_pro):
            return None
        for wvpssh, prpssh in zip(self.wv_pssh, self.mspr_pro):
            keys = await get_clear_key(wvpssh, prpssh, self.assertion, self.drm_type)
            if keys:
                for key in keys:
                    await self.save_key(key)
                return keys
            logger.warning("No keys received")
            return None
        return None

    def _normalize_drm_type(self, drm_type: str) -> str:
        """正規化 DRM 類型"""
        try:
            drm_type = drm_type.lower().strip()
        except AttributeError:
            drm_type = "widevine"
        valid = {
            "playready",
            "widevine",
            "remote_widevine",
            "remote_playready",
            "watora",
            "http_api",
            "none",
        }
        if drm_type not in valid:
            ConfigLoader.print_warning("DRM-Key Service", drm_type, "Widevine")
            logger.warning(f"Unsupported drm choice: {Color.fg('ruby')}{drm_type}{Color.fg('gold')}, fallback to Widevine ...")
            drm_type = "widevine"
        return drm_type
