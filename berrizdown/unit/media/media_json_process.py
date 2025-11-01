from typing import Any


class MediaJsonProcessor:
    """A class for processing JSON media data and extracting relevant information."""

    @staticmethod
    def process_selection(
        selected_media: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """Process the selected media dictionary and return categorized media items."""
        processed: dict[str, list[dict[str, Any]]] = {
            "vods": [],
            "photos": [],
            "lives": [],
            "post": [],
        }

        # Process VODs
        if "vods" in selected_media and selected_media["vods"]:
            processed["vods"] = [item for item in selected_media["vods"] if isinstance(item, dict) and "mediaId" in item and "mediaType" in item]

        # Process Live-replays
        if "lives" in selected_media and selected_media["lives"]:
            processed["lives"] = [item for item in selected_media["lives"] if isinstance(item, dict) and "mediaId" in item and "mediaType" in item]

        # Process Photos
        if "photos" in selected_media and selected_media["photos"]:
            processed["photos"] = [item for item in selected_media["photos"] if isinstance(item, dict) and "mediaId" in item and "mediaType" in item]

        # Process Post
        if "post" in selected_media and selected_media["post"]:
            processed["post"] = [item for item in selected_media["post"] if isinstance(item, dict) and "mediaId" in item and "mediaType" in item]

        # Process Notice
        if "notice" in selected_media and selected_media["notice"]:
            processed["notice"] = [item for item in selected_media["notice"] if isinstance(item, dict) and "mediaId" in item and "mediaType" in item]

        # Process CMT
        if "cmt" in selected_media and selected_media["cmt"]:
            processed["cmt"] = [item for item in selected_media["cmt"] if isinstance(item, dict) and "contentId" in item and "contentType" in item]
        return processed
