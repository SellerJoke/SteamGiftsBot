import time
from pathlib import Path

import dill

from src.const.path import ROOT_DIR
from src.object.auxiliary import Status
from src.util.file import create_file_if_not_exists


class StatusIO:
    """读写应用状态的类"""
    _STATUS_PATH: Path = Path(ROOT_DIR) / "resources" / "persistence" / "status.dill"
    _DEFAULT_STATUS: Status = Status(points=None, points_update_timestamp=None, xsrf_token=None)
    _status: Status = None

    @classmethod
    def load(cls):
        """加载状态"""
        if not cls._STATUS_PATH.is_file():
            cls._status = cls._DEFAULT_STATUS
        else:
            with open(cls._STATUS_PATH, "rb") as f:
                cls._status = dill.load(f)
        return cls._status

    @classmethod
    def save_xsrf_token(cls, xsrf_token: str):
        """保存xsrf_token"""
        if cls._status is None:
            raise Exception("保存xsrf_token前必须先加载状态")
        if cls._status["xsrf_token"] != xsrf_token:
            cls._status["xsrf_token"] = xsrf_token
            cls.__save()

    @classmethod
    def save_points(cls, points: int, points_update_timestamp: int | None = None):
        """保存点数"""
        if cls._status is None:
            raise Exception("保存点数前必须先加载状态")
        if points_update_timestamp is None:
            points_update_timestamp = int(time.time())
        if cls._status["points_update_timestamp"] != points_update_timestamp:
            cls._status["points"] = points
            cls._status["points_update_timestamp"] = points_update_timestamp
            cls.__save()

    @classmethod
    def __save(cls):
        """保存状态"""
        if cls._status is None:
            raise Exception("保存状态前必须先加载状态")
        create_file_if_not_exists(cls._STATUS_PATH)
        with open(cls._STATUS_PATH, "wb") as f:
            dill.dump(cls._status, f)


if __name__ == "__main__":
    print(StatusIO.load())
