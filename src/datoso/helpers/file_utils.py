"""File utils."""
import os
import shutil
from contextlib import suppress
from pathlib import Path


def copy_path(origin: str | Path, destination: str | Path) -> None:
    """Copy file to destination."""
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    try:
        if Path(origin).is_dir():
            with suppress(FileNotFoundError):
                shutil.rmtree(destination)
            shutil.copytree(origin, destination)
        else:
            shutil.copy(origin, destination)
    except shutil.SameFileError:
        pass
    except FileNotFoundError:
        msg = f'File {origin} not found.'
        raise FileNotFoundError(msg) from None

def remove_folder(path: str | Path) -> None:
    """Remove folder."""
    with suppress(PermissionError):
        shutil.rmtree(path)

def remove_path(pathstring: str | Path, *, remove_empty_parent: bool = False) -> None:
    """Remove file or folder."""
    path = pathstring if isinstance(pathstring, Path) else parse_path(pathstring)
    if not path.exists():
        return
    if path.is_dir():
        remove_folder(path)
    else:
        path.unlink()
    if remove_empty_parent and not list(path.parent.iterdir()):
        remove_path(path.parent, remove_empty_parent=True)

def remove_empty_folders(path_abs: str | Path) -> None:
    """Remove empty folders."""
    walk = list(os.walk(str(path_abs)))
    for path, _, _ in walk[::-1]:
        if not any(Path(path).iterdir()):
            remove_path(path)

def parse_path(path: str) -> Path:
    """Get folder from config."""
    path = path if path is not None else ''
    if path.startswith('~'):
        return Path(path).expanduser()
    return Path.cwd() / path

def move_path(origin: str | Path, destination: str | Path) -> None:
    """Move file to destination."""
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(origin, destination)
    except shutil.Error:
        remove_path(origin)

def get_ext(path: str | Path) -> str:
    """Get extension of file."""
    return Path(path).suffix
