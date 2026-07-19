from pathlib import Path

# 定位项目根目录
_directory: Path = Path(__file__).resolve().parent
while not (_directory / 'README.md').is_file():
    parent_dir = _directory.parent
    if parent_dir == _directory:
        raise FileNotFoundError("找不到README.md文件，无法定位项目根目录")
    _directory = parent_dir
ROOT_DIR: Path = _directory

if __name__ == "__main__":
    print(ROOT_DIR)
