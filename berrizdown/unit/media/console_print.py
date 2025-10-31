from static.color import Color
from static.PlaybackInfo import PlaybackInfo
from unit.handle.handle_log import setup_logging

logger = setup_logging("console_print", "cyan")


def print_title(
    public_info: PlaybackInfo,
    playback_info: PlaybackInfo,
    key_handler: object | None = None,
    drm_key: str | None = None,
):
    logger.info(f"{Color.bold()}{Color.fg('bright_yellow')}Title:{Color.reset()} {Color.fg('light_yellow')}{public_info.title}{Color.reset()}")
    logger.info(f"{Color.bold()}{Color.fg('bright_cyan')}MediaType:{Color.reset()} {Color.fg('light_cyan')}{public_info.media_type}{Color.reset()}")
    logger.info(f"{Color.bold()}{Color.fg('bright_magenta')}Media ID:{Color.reset()} {Color.fg('magenta')}{public_info.media_id}{Color.reset()}")

    logger.info(f"{Color.fg('sky_blue')}Thumbnail URL:{Color.reset()} {Color.fg('light_blue')}{public_info.thumbnail_url}{Color.reset()}")

    logger.info(f"{Color.bold()}{Color.fg('bright_red')}Fanclub Only:{Color.reset()} {Color.fg('light_red')}{public_info.is_fanclub_only}{Color.reset()}")

    logger.info(f"{Color.fg('lime')}Community ID:{Color.reset()} {Color.fg('light_green')}{public_info.community_id}{Color.reset()}")
    logger.info(f"{Color.fg('light_gray')}Published At:{Color.reset()} {Color.fg('snow')}{public_info.published_at}{Color.reset()}")

    if public_info.categories:
        logger.info(f"{Color.bold()}{Color.fg('peach')}Category:{Color.reset()} {Color.fg('light_magenta')}{public_info.categories[0]['name']}{Color.reset()}")

    minutes = playback_info.duration // 60
    seconds = playback_info.duration % 60
    logger.info(f"{Color.fg('light_amber')}Duration:{Color.reset()} {Color.bold()}{Color.fg('gold')}{minutes} min {seconds} sec{Color.reset()}")

    logger.info(f"{Color.fg('azure')}Orientation:{Color.reset()} {Color.fg('light_cyan')}{playback_info.orientation}{Color.reset()}")

    if playback_info.is_drm:
        logger.info(f"{Color.bold()}{Color.bg('maroon')}{Color.fg('bright_white')} DRM ENABLED {Color.reset()}")

    for i, artist in enumerate(public_info.artists):
        header = f" ARTIST {i + 1} "
        logger.info(f"{Color.bg('gold')}{Color.fg('black')}{header}{Color.reset()}")
        logger.info(f"{Color.fg('navy')}ID:{Color.reset()} {Color.fg('olive')}{artist['id']}{Color.reset()}")
        logger.info(f"{Color.fg('violet')}Name:{Color.reset()} {Color.fg('light_magenta')}{artist['name']}{Color.reset()}")
        logger.info(f"{Color.fg('turquoise')}Image:{Color.reset()} {Color.fg('light_cyan')}{artist['image_url']}{Color.reset()}")

    def add_pssh_row(label: str, values: list[str] | None):
        if values:
            joined = " ".join(values)
            color = "bright_green" if label.lower().startswith("widevine") else "bright_magenta"
            logger.info(f"{Color.bold()}{Color.fg(color)}{label} PSSH:{Color.reset()} {Color.fg('light_gray')}{joined}{Color.reset()}")

    if key_handler:
        add_pssh_row("Widevine", getattr(key_handler, "wv_pssh", None))
        add_pssh_row("PlayReady", getattr(key_handler, "msprpro", None))

    if getattr(playback_info, "dash_playback_url", None):
        logger.info(f"{Color.bg('azure')}{Color.fg('black')} MPD (DASH) {Color.reset()} {Color.fg('bright_cyan')}{playback_info.dash_playback_url}{Color.reset()}")
    if getattr(playback_info, "hls_playback_url", None):
        logger.info(f"{Color.bg('light_blue')}{Color.fg('black')} HLS (m3u8) {Color.reset()} {Color.fg('bright_cyan')}{playback_info.hls_playback_url}{Color.reset()}")

    if drm_key:
        logger.info(f"{Color.bold()}{Color.fg('bright_red')}CONTENT KEYS:{Color.reset()}")
        for key in drm_key:
            logger.info(f"{Color.bg('dark_gray')}{Color.fg('light_white')} {key} {Color.reset()}")
