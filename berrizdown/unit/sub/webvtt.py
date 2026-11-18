import re


RE_WEBVTT_HEADER = re.compile(r"(?m)^WEBVTT\s*$")
RE_CUE_TIMING = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})"
)


def parse_vtt_timestamp(timestamp: str) -> int:
    hours, minutes, rest = timestamp.split(":")
    seconds, milliseconds = rest.split(".")
    return (
        int(hours) * 3_600_000_000
        + int(minutes) * 60_000_000
        + int(seconds) * 1_000_000
        + int(milliseconds) * 1_000
    )


def format_vtt_timestamp(microseconds: int) -> str:
    total_ms = microseconds // 1000
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def parse_vtt_block(block: str) -> list[dict]:
    lines = block.splitlines()
    cues: list[dict] = []
    current_start: int | None = None
    current_end: int | None = None
    current_text_lines: list[str] = []

    def flush_cue() -> None:
        nonlocal current_start, current_end, current_text_lines
        if current_start is not None and current_end is not None and current_text_lines:
            cues.append(
                {
                    "start": current_start,
                    "end": current_end,
                    "text": "\n".join(current_text_lines).strip(),
                }
            )
        current_start = None
        current_end = None
        current_text_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == "WEBVTT" or stripped.startswith("X-TIMESTAMP-MAP"):
            continue
        timing_match = RE_CUE_TIMING.match(stripped)
        if timing_match:
            flush_cue()
            current_start = parse_vtt_timestamp(timing_match.group(1))
            current_end = parse_vtt_timestamp(timing_match.group(2))
            continue
        if stripped == "":
            flush_cue()
            continue
        if current_start is not None:
            current_text_lines.append(line)
    flush_cue()
    return cues


def merge_adjacent_duplicates(cues: list[dict], tolerance_us: int = 1000) -> list[dict]:
    if not cues:
        return []
    merged: list[dict] = [cues[0]]
    for cue in cues[1:]:
        previous = merged[-1]
        if (
            cue["text"] == previous["text"]
            and (cue["start"] - previous["end"]) <= tolerance_us
        ):
            previous["end"] = max(previous["end"], cue["end"])
        else:
            merged.append(cue)
    return merged


def merge_segmented_webvtt(vtt_raw: str) -> str:
    segments = [f"WEBVTT\n{block}" for block in re.split(r"WEBVTT", vtt_raw) if block.strip()]

    all_cues: list[dict] = []
    for segment in segments:
        all_cues.extend(parse_vtt_block(segment))

    if not all_cues:
        return "WEBVTT\n"

    all_cues.sort(key=lambda c: c["start"])
    all_cues = merge_adjacent_duplicates(all_cues)

    output_lines = ["WEBVTT", ""]
    for cue in all_cues:
        output_lines.append(
            f"{format_vtt_timestamp(cue['start'])} --> {format_vtt_timestamp(cue['end'])}"
        )
        output_lines.append(cue["text"])
        output_lines.append("")

    return "\n".join(output_lines)