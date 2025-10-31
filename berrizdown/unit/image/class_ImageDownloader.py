import asyncio
import random
import shutil
from io import BytesIO
from typing import Any

from lib.__init__ import printer_video_folder_path_info, resolve_conflict_path
from lib.path import Path
from static.color import Color
from unit.__init__ import USERAGENT, FilenameSanitizer
from unit.handle.handle_log import setup_logging
from unit.http.request_berriz_api import GetRequest

logger = setup_logging("class_ImageDownloader", "sienna")
semaphore: asyncio.Semaphore = asyncio.Semaphore(7)


class ImageDownloader:
    """Handles downloading images from URLs using aiohttp and shutil for async-safe file I/O."""

    def __init__(self) -> None:
        self.getrequest: GetRequest = GetRequest()
        self.header: dict[str, str] = {
            "user-agent": USERAGENT,
            "accept-encoding": "identity",
            "accept": "image/avif,image/webp,image/png,image/jpeg,image/gif,image/svg+xml,*/*",
        }
        self._file_write_max_retries = 3

    async def _write_to_file(self, response: bytes, target_file_path: str | Path) -> None:
        """Write raw bytes to file using shutil.copyfileobj wrapped in asyncio.to_thread."""
        file_path: Path = Path(target_file_path).parent / FilenameSanitizer.sanitize_filename(Path(target_file_path).name)
        resolvepath = await resolve_conflict_path(file_path)

        for attempt in range(1, self._file_write_max_retries + 1):
            try:
                async with semaphore:
                    await asyncio.to_thread(self._write_bytes_with_shutil, response, resolvepath)
                    printer_video_folder_path_info(
                        resolvepath,
                        resolvepath.name,
                        f"{Color.fg('sunrise')}Image {Color.reset()}",
                    )
                    return

            except OSError as e:
                if attempt == self._file_write_max_retries:
                    logger.error(f"File write failed after {self._file_write_max_retries} attempts: {resolvepath} - {e}")
                    if resolvepath.exists():
                        try:
                            resolvepath.unlink()
                            logger.info(f"Cleaned up failed file: {resolvepath}")
                        except Exception as cleanup_err:
                            logger.warning(f"Failed to clean up file {resolvepath}: {cleanup_err}")
                backoff = (2 ** (attempt - 1)) * 0.5
                jitter = random.uniform(0, 0.1 * backoff)
                wait_time = backoff + jitter
                logger.warning(f"[File Write Attempt {attempt}/{self._file_write_max_retries}] Failed: {resolvepath} - {e}, retrying in {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            except asyncio.CancelledError:
                if resolvepath.exists():
                    try:
                        resolvepath.unlink()
                        logger.info(f"Removed partial file: {resolvepath}")
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to clean up file {resolvepath}: {cleanup_err}")
                raise

    def _write_bytes_with_shutil(self, data: bytes, path: Path) -> None:
        """Use shutil to write bytes to file with fixed buffer size."""
        with open(path, "wb") as f:
            shutil.copyfileobj(BytesIO(data), f, length=4 * 1024 * 1024)

    async def download_image(self, url: str) -> bytes | None:
        """Download image and return raw bytes. Caller handles saving."""
        params = {}
        use_proxy = False
        usecookie = False
        bytes_data: Any = await self.getrequest._send_request("get", url, params, self.header, use_proxy, usecookie, response_object=False)
        if not isinstance(bytes_data, bytes):
            logger.error(f"Failed to download image: {url}, got response: {bytes_data}s")
            raise ValueError("Response is not bytes")
        return bytes_data
