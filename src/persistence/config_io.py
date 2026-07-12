import copy
import re
from pathlib import Path
from typing import Any

import yaml

from src.const.path import ROOT_DIR


class ConfigIO:
    """读取配置文件的类"""
    FILE_PATH: Path = Path(ROOT_DIR) / "resources" / "config.yml"
    _DEFAULT_CONFIG: dict[str, Any] = {
        "debug": False,
        "PHPSESSID": None
    }
    _PHPSESSID_REGEX = re.compile(r"^[a-z0-9]{48}$")

    @classmethod
    def load(cls) -> dict[str, Any]:
        """获取配置文件内容"""
        if not cls.FILE_PATH.is_file():
            return copy.deepcopy(cls._DEFAULT_CONFIG)
        with open(cls.FILE_PATH, "r", encoding="utf-8") as f:
            config: dict[str, Any] = yaml.safe_load(f)
            phpsessid: str | None = config.get("phpsessid")
            if phpsessid and not cls.validate_phpsessid(phpsessid):
                raise Exception(f"{cls.FILE_PATH}配置文件中的phpsessid格式不正确，应为48位小写字母、数字的组合，请检查")
            return config

    @classmethod
    def validate_phpsessid(cls, phpsessid: str) -> bool:
        """验证phpsessid格式"""
        return cls._PHPSESSID_REGEX.fullmatch(phpsessid) is not None


if __name__ == "__main__":
    pass
