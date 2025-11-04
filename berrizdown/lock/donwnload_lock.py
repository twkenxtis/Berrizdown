import atexit
import os
import queue
import sqlite3
import threading
import time

from berrizdown.lib.path import Path
from berrizdown.static.route import Route
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("download_lock", "forest_green")

DB: Path = Route().download_info_db


class UUIDSetStore:
    def __init__(self) -> None:
        lock_dir: str = os.path.join(os.getcwd(), "berrizdown", "lock")
        os.makedirs(lock_dir, exist_ok=True)

        self.filename: str = os.path.join(lock_dir, DB)
        self.lock: threading.Lock = threading.Lock()

        self.task_queue: queue.Queue[str] = queue.Queue()
        self.stop_event: threading.Event = threading.Event()
        self.flush_interval: int = 1

        self.buffer: list[str] = []
        self.buffer_limit = 100
        self.last_flush_time = time.time()

        self.worker_thread: threading.Thread = threading.Thread(target=self._worker, daemon=True)

        self._init_db()
        self.worker_thread.start()
        atexit.register(self.stop)

    def _init_db(self) -> None:
        with self.lock:
            conn = sqlite3.connect(self.filename)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS uuid_set (
                    uuid TEXT PRIMARY KEY
                )
                """
            )
            conn.commit()
            conn.close()

    def _flush_buffer_to_db(self) -> None:
        if not self.buffer:
            return
        try:
            with self.lock:
                conn = sqlite3.connect(self.filename)
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT OR IGNORE INTO uuid_set (uuid) VALUES (?)",
                    [(u,) for u in self.buffer],
                )
                conn.commit()
                conn.close()
            self.buffer.clear()
        except Exception as e:
            logger.error(f"[UUIDSetStore] Batch DB insert failed: {e}")

    def _worker(self) -> None:
        while not self.stop_event.is_set() or not self.task_queue.empty() or self.buffer:
            try:
                uuid_str: str = self.task_queue.get(timeout=self.flush_interval)
                self.buffer.append(uuid_str)
                self.task_queue.task_done()
            except queue.Empty:
                pass

            if len(self.buffer) >= self.buffer_limit or (time.time() - self.last_flush_time) >= self.flush_interval:
                self._flush_buffer_to_db()
                self.last_flush_time = time.time()

    def add(self, uuid_str: str) -> None:
        if not isinstance(uuid_str, str):
            raise ValueError("UUID must be a string")
        self.task_queue.put(uuid_str)

    def exists(self, uuid_str: str) -> bool:
        with self.lock:
            conn = sqlite3.connect(self.filename)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM uuid_set WHERE uuid = ?", (uuid_str,))
            exists = cursor.fetchone() is not None
            conn.close()
        return exists

    def stop(self) -> None:
        try:
            if not self.stop_event.is_set():
                self.stop_event.set()
                self.worker_thread.join()
                # Ensure remaining buffered UUIDs are saved
                self._flush_buffer_to_db()
        except KeyboardInterrupt:
            pass
