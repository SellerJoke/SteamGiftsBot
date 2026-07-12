from pathlib import Path


def create_dir_if_not_exists(path: Path | str):
    """如果目录不存在则创建"""
    if isinstance(path, str):
        path = Path(path)
    if path.is_file():
        path.unlink()
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)

def create_file_if_not_exists(filepath: Path | str):
    """如果文件不存在则创建"""
    if isinstance(filepath, str):
        filepath = Path(filepath)
    if filepath.parent.is_file():
        filepath.parent.unlink()
    if not filepath.parent.is_dir():
        filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.is_dir():
        filepath.rmdir()
    filepath.touch(exist_ok=True)
