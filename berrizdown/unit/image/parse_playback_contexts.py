from typing import Any


class IMG_PlaybackContext:
    def __init__(self, playback_contexts: list[dict[str, Any]]) -> None:
        if not playback_contexts:
            raise ValueError("public_contexts is empty")

        ctx: dict[str, Any] = playback_contexts[0]

        # root
        self.code: Any = ctx.get("code")
        self.message: Any = ctx.get("message")
        data: dict[str, Any] = ctx.get("data", {})

        # data
        self.vod: Any = data.get("vod")
        photo: dict[str, Any] = data.get("photo", {})
        self.youtube: Any = data.get("youtube")
        self.tracking: Any = data.get("tracking")
        self.settlement: Any = data.get("settlement")

        # photo
        self.image_count: Any = photo.get("imageCount")
        self.images: list[Any] = photo.get("images", [])
