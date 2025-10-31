import shutil
from pathlib import Path


def get_binary_path(*names: str) -> Path | None:
    """Get the path of the first found binary name."""
    for name in names:
        path = shutil.which(name)
        if path:
            return Path(path)
    return None
