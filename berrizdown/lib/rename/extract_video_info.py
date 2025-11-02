import asyncio

from lib.mux.videoinfo import VideoInfo
from lib.path import Path
from static.parameter import paramstore
from unit.handle.handle_log import setup_logging

logger = setup_logging("extract_video_info", "dark_green")


async def extract_video_info(path: Path) -> tuple[str, str, str]:
    """異步提取最終 MP4 檔案的編解碼器、畫質標籤和音頻編解碼器"""
    vv: VideoInfo = VideoInfo(path)

    # 使用 TaskGroup 並將 FFmpeg 探針的同步操作包裝成異步
    async with asyncio.TaskGroup() as tg:
        codec_task: asyncio.Task[str] = tg.create_task(asyncio.to_thread(lambda: vv.codec))
        quality_task: asyncio.Task[str] = tg.create_task(asyncio.to_thread(lambda: vv.quality_label))
        audio_task: asyncio.Task[str] = tg.create_task(asyncio.to_thread(lambda: vv.audio_codec))
    video_codec: str = codec_task.result()
    video_quality_label: str = quality_task.result()
    video_audio_codec: str = audio_task.result()
    if video_audio_codec == "unknown":
        if paramstore.get("no_video_audio") is True:
            video_audio_codec = "{audio}"
        else:
            logger.warning(f"Unknown audio codec: {video_audio_codec}")
            video_audio_codec = "x"
    if video_codec == "unknown":
        if paramstore.get("no_video_audio") is True:
            video_codec = "{video}"
        else:
            logger.warning(f"Unknown video codec: {video_codec}")
            video_codec = "x"
    return video_codec, video_quality_label, video_audio_codec
