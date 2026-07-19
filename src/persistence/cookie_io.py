import logging
import time
from pathlib import Path

import dill
from httpx import Cookies

from src.const.path import ROOT_DIR
from src.util.file import create_file_if_not_exists


class CookieIO:
    """读取和保存Cookie的类"""
    LOGGER: logging.Logger = logging.getLogger(__name__).getChild("CookieIO")
    # cookie文件保存在项目下的路径
    __COOKIE_PATH: Path = ROOT_DIR / "resources" / "persistence" / "cookies.dill"
    # Cookie保存时间间隔：10分钟（暂定）
    __COOKIE_SAVE_INTERVAL: int = 10 * 60
    # 上次保存Cookie的时间
    __save_time: float = 0
    # 从文件加载的Cookie，每次保存新Cookie到本地文件时，也会更新此字段
    __cookies: Cookies

    @classmethod
    def save(cls, cookies: Cookies) -> None:
        """
        满足以下任意条件，保存Cookies到本地文件
        1. 要保存的Cookies和现存的Cookies至少有1个字段不相同
        2. 上次保存时间超过10分钟（暂定）
        """
        if cls.__cookies != cookies or time.time() - cls.__save_time > cls.__COOKIE_SAVE_INTERVAL:
            cls.__save(cookies)

    @classmethod
    def load(cls) -> Cookies:
        """从本地文件中加载Cookies"""
        cls.__save_time = 0
        with open(cls.__COOKIE_PATH, "rb") as file:
            cls.__cookies = Cookies(dill.load(file))
            return Cookies(cls.__cookies)

    @classmethod
    def __save(cls, cookies: Cookies):
        """保存Cookies到本地文件"""
        cls.__update_cookies(cookies)
        cls.__save_time = time.time()
        create_file_if_not_exists(cls.__COOKIE_PATH)
        with open(cls.__COOKIE_PATH, "wb") as file:
            dill.dump(cls.__cookies, file)

    @classmethod
    def __update_cookies(cls, cookies: Cookies) -> None:
        """更新__cookies变量"""
        if not hasattr(cls, "__cookies") or cls.__cookies is None:
            cls.__cookies = cookies
        else:
            cls.__cookies.update(cookies)

    @classmethod
    def _initialize(cls):
        """初始化CookieIO类变量"""
        # 确保cookie文件存在，并将本地文件中保存的Cookies赋值给__cookies变量
        if not cls.__COOKIE_PATH.is_file():
            cls.__save(Cookies())
        else:
            with open(cls.__COOKIE_PATH, "rb") as file:
                cls.__cookies = Cookies(dill.load(file))


# noinspection PyProtectedMember
CookieIO._initialize()

if __name__ == '__main__':
    pass