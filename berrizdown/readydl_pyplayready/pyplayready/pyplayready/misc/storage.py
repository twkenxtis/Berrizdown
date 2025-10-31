from pathlib import Path

from platformdirs import user_data_dir


class Storage:
    @staticmethod
    def _get_initialized_path() -> Path:
        storage_path = Path(user_data_dir("pyplayready", "DevLARLEY"))
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    @staticmethod
    def write_file(file_name: str, data: bytes) -> bool:
        storage_path = Storage._get_initialized_path()
        storage_file = storage_path / file_name

        new_file = not storage_file.exists()

        storage_file.write_bytes(data)

        return new_file

    @staticmethod
    def read_file(file_name: str) -> bytes | None:
        storage_path = Storage._get_initialized_path()
        storage_file = storage_path / file_name

        if not storage_file.exists():
            return None

        return storage_file.read_bytes()
