import os

# 下面的步骤是为了定位项目根目录，假设项目根目录下有 README.md 文件
_directory: str = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_directory, 'README.md')):
    parent_dir = os.path.dirname(_directory)
    if parent_dir == _directory:  # 已经到系统根目录
        raise FileNotFoundError("找不到README.md文件，无法定位项目根目录")
    _directory = parent_dir
ROOT_DIR = _directory

if __name__ == "__main__":
    pass