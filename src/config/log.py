import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any

from src.const.path import ROOT_DIR
from src.persistence.config_io import ConfigIO
from src.util.file import create_dir_if_not_exists


class _DateTimeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, base_dir, mode: str='a', max_bytes: int=0, backup_count: int=0, encoding: str | None=None,
                 delay: bool=False, errors: str | None=None):
        """
        自定义滚动日志处理器：
        - 每个日志文件都使用"被创建时的时间"作为文件名
        - 达到 max_bytes时自动滚动，新建一个以当前时间命名的文件
        - backup_count=0时永久保留所有历史文件
        """
        self.base_dir = base_dir
        create_dir_if_not_exists(base_dir)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        init_file = os.path.join(base_dir, f"{current_time}.log")
        super().__init__(init_file, mode=mode, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding,
                         delay=delay, errors=errors)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        # 关键：滚动时用"当前时间"作为新日志文件的文件名
        self.baseFilename = os.path.abspath(
            os.path.join(self.base_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        )

        # 不做旧文件的重命名/删除，每个滚动文件都保留自己的时间戳文件名
        # 如果设置了 backupCount > 0，则按创建时间删除最旧的文件
        if self.backupCount > 0:
            files = sorted(
                [f for f in os.listdir(self.base_dir) if f.endswith(".log")],
                reverse=True,
            )
            for old_file in files[self.backupCount:]:
                try:
                    os.remove(os.path.join(self.base_dir, old_file))
                except OSError:
                    pass

        if not self.delay:
            self.stream = self._open()


def setup_logging():
    """配置日志"""
    config: dict[str, Any] = ConfigIO.load()
    log_config: dict[str, Any] = config.get("logging", {})
    destinations: list[str] = log_config.get("destinations", [])
    handlers = {
        "console": logging.StreamHandler(sys.stdout),
        "file": _DateTimeRotatingFileHandler(base_dir=os.path.join(ROOT_DIR, "log"), max_bytes=16 * 1024 * 1024,
                                             backup_count=49, encoding="utf-8"),
    }
    handlers = [handlers[dest] for dest in destinations]
    # noinspection SpellCheckingInspection
    logging.basicConfig(level=log_config.get("level", "INFO"), handlers=handlers, datefmt="%Y-%m-%d %H:%M:%S",
                        format="%(asctime)s.%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s: %(message)s")
    if log_config.get("show-sql", False):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    if log_config.get("debug", False):
        logging.getLogger("src").setLevel(logging.DEBUG)
