from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text
from static.PlaybackInfo import PlaybackInfo


def print_title(
    public_info: PlaybackInfo,
    playback_info: PlaybackInfo,
    key_handler: object | None = None,
    drm_key: str | None = None,
):
    table = Table(show_header=False, show_lines=False, box=box.ROUNDED, border_style="bright_blue")
    table.add_column("Label", style="cyan", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")

    title_text = Text(str(public_info.title), style="yellow")
    media_id_text = Text(str(public_info.media_id), style="magenta")

    minutes = playback_info.duration // 60
    seconds = playback_info.duration % 60
    duration_text = Text()
    duration_text.append(f"{minutes}", style="green")
    duration_text.append(" min ", style="cyan")
    duration_text.append(f"{seconds}", style="green")
    duration_text.append(" second", style="yellow")

    drm_text = Text("DRM", style="red") if playback_info.is_drm else Text("")

    table.add_row("Title", title_text)
    table.add_row("MediaType", str(public_info.media_type))
    table.add_row("Media ID", media_id_text)
    table.add_row("Thumbnail URL", str(public_info.thumbnail_url))
    table.add_row("Fanclub Only", str(public_info.is_fanclub_only))
    table.add_row("Community ID", str(public_info.community_id))
    table.add_row("Published At", str(public_info.published_at))
    if public_info.categories:
        table.add_row("Category", str(public_info.categories[0]["name"]))
    table.add_row("Duration", duration_text)
    table.add_row("Orientation", str(playback_info.orientation))
    table.add_row("DRM", drm_text)

    # Artists
    for i, artist in enumerate(public_info.artists):
        prefix = f"Artist {i + 1}"
        table.add_row(f"{prefix} ID", str(artist["id"]))
        table.add_row(f"{prefix} Name", str(artist["name"]))
        table.add_row(f"{prefix} Image", str(artist["image_url"]))

    def add_pssh_row(label: str, values: list[str] | None, color: str):
        if values:
            joined = " ".join(values)
            table.add_row(f"{label} PSSH", Text(joined, style=color))

    if key_handler:
        add_pssh_row("Widevine", getattr(key_handler, "wv_pssh", None), "bright_green")
        add_pssh_row("PlayReady", getattr(key_handler, "msprpro", None), "bright_magenta")

    if getattr(playback_info, "dash_playback_url", None):
        table.add_row(
            "MPD (DASH)",
            Text(str(playback_info.dash_playback_url), style="bright_cyan"),
        )
    if getattr(playback_info, "hls_playback_url", None):
        table.add_row("HLS (m3u8)", Text(str(playback_info.hls_playback_url), style="bright_cyan"))
    if drm_key is not None:
        for key in drm_key:
            table.add_row("Content Key", Text(key, style="bright_red"))

    console = Console()
    console.print(table)
