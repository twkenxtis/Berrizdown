import time
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text


class MultiTrackProgressManager:
    _instance: Optional["MultiTrackProgressManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.console = Console()
        self.progress_bars: dict[str, ProgressBar] = {}
        self.live: Live | None = None
        self._initialized = True

    def create_progress_bar(self, track_type: str, total: int, video_duration: str) -> "ProgressBar":
        progress_bar = ProgressBar(total=total, video_duration=video_duration, prefix=track_type, manager=self)
        self.progress_bars[track_type] = progress_bar
        return progress_bar

    def _generate_table(self) -> Table:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
        table.add_column("Progress", no_wrap=False)

        for track_type, pb in self.progress_bars.items():
            table.add_row(pb._generate_rich_text())

        return table

    def start(self):
        if self.live is None:
            self.live = Live(
                self._generate_table(),
                console=self.console,
                refresh_per_second=10,
                transient=False,
            )
            self.live.start()

    def update(self):
        if self.live:
            self.live.update(self._generate_table())

    def stop(self):
        if self.live:
            self.live.stop()
            self.live = None

    def remove_all_progress_bars(self):
        """移除所有進度條"""
        for track_type, pb in list(self.progress_bars.items()):
            if hasattr(pb, "unlink") and callable(pb.unlink):
                pb.unlink()
        self.progress_bars.clear()
        self.update()


class ProgressBar:
    def __init__(
        self,
        total: int,
        video_duration: str,
        prefix: str = "",
        length: int = 80,
        manager: MultiTrackProgressManager | None = None,
    ):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.current = 0
        self.manager = manager

        self.console = Console() if manager is None else manager.console

        self.speed_mbps: float = 0.0
        self.downloaded_mb: float = 0.0
        self.eta_seconds: float = 0.0
        self.start_time: float = time.time()

        self.fps: float = 0.0
        self.codec: str = ""
        self.ping_ms: float = 0.0
        self.total_size_mb: float = 0.0
        self.duration_seconds: str = video_duration

    def _generate_rich_text(self) -> Text:
        percent = self.current / self.total if self.total > 0 else 0

        text = Text()
        text.append(f"{self.prefix:6}", style="cyan")
        text.append(": ")
        text.append(f"{percent * 100:6.2f} ", style="white")
        text.append("% ", style="gray")
        text.append("| ")
        text.append(f"{self.current}/{self.total}", style="yellow")
        text.append(" | ")
        text.append(f"{self.speed_mbps:5.2f}", style="green")
        text.append(" MB/s ", style="gray")
        text.append("| ")
        text.append(f"{self.downloaded_mb:6.1f}", style="blue")
        text.append(" MB ", style="gray")
        text.append("| ETA: ")
        text.append(self._format_time(self.eta_seconds), style="magenta")
        text.append(" | ")
        text.append(self.duration_seconds, style="purple")

        extra_info = []
        if self.codec:
            extra_info.append((self.codec, "cyan"))
        if self.fps > 0:
            extra_info.append((f"{self.fps:.1f}fps", "yellow"))
        if self.ping_ms > 0:
            extra_info.append((f"{self.ping_ms:.0f}ms", "red"))
        if self.total_size_mb > 0:
            extra_info.append((f"~{self.total_size_mb:.1f}MB", "blue"))

        if extra_info:
            text.append(" | ")
            for i, (info_text, style) in enumerate(extra_info):
                if i > 0:
                    text.append(" ")
                text.append(info_text, style=style)

        return text

    def update(self, progress: int = None, download_progress: object | None = None):
        if download_progress is not None:
            self.current = download_progress.completed_segments
            self.speed_mbps = download_progress.speed_mbps
            self.downloaded_mb = download_progress.current_bytes / 1024 / 1024
            self.eta_seconds = download_progress.eta_seconds

            if hasattr(download_progress, "fps"):
                self.fps = download_progress.fps
            if hasattr(download_progress, "codec"):
                self.codec = download_progress.codec
            if hasattr(download_progress, "ping_ms"):
                self.ping_ms = download_progress.ping_ms
            if hasattr(download_progress, "total_size_mb"):
                self.total_size_mb = download_progress.total_size_mb

        elif progress is not None:
            self.current = progress
        else:
            self.current += 1

        if self.manager:
            self.manager.update()

    def _format_time(self, seconds: float) -> str:
        """格式化時間顯示"""
        if seconds <= 0 or seconds > 86400:
            return "--:--"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        elif minutes > 0:
            return f"{minutes}m{secs:02d}s"
        else:
            return f"{secs}s"
