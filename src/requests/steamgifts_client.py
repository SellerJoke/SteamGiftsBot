import locale
import logging
import time
from typing import Any, Literal

from bs4 import BeautifulSoup, Tag
from httpx import Response

from src.object.auxiliary import GiveawayData, Status
from src.object.persistent.giveaway import Giveaway
# noinspection PyUnusedImports
from src.object.persistent.steam_app import SteamApp
# noinspection PyUnusedImports
from src.object.persistent.steam_package import SteamPackage
# noinspection PyUnusedImports
from src.object.persistent.user import User
from src.persistence.config_io import ConfigIO
from src.persistence.status_io import StatusIO
from src.requests.retry_client import RetryClient
from src.util.convertor import data2giveaway


class SteamGiftsClient:
    """与SteamGifts进行请求交互的客户端"""
    LOGGER: logging.Logger = None
    _STEAMGIFTS_HOMEPAGE_URL = "https://www.steamgifts.com/"
    _GIVEAWAY_LIST_URL = "https://www.steamgifts.com/giveaways/search"
    _INSERT_DELETE_ENTRY_URL = "https://www.steamgifts.com/ajax.php"
    _LOGIN_SELECTOR = "html > body > header > nav > div.nav__right-container > div.nav__button-container > a.nav__sits"
    _POINTS_SELECTOR = "html > body > header > nav > div.nav__right-container > div.nav__button-container > a.nav__button.nav__button--is-dropdown > span.nav__points"
    _XSRF_SELECTOR = "html > body > div.popup.popup--hide-games > form > input[name='xsrf_token']"

    def __init__(self):
        """
        初始化SteamGifts客户端流程
        1. 尝试从本地文件读取cookie、_xsrf_token、points、points_update_timestamp
        2. 如果本地文件存在上述值，将cookie应用在_client中，_xsrf_token、points、points_update_timestamp赋值到此类相应字段
        3. 使用_client获取首页soup，更新_index_soup字段，从首页soup中获取登录状态
        4. 如果登录状态为已登录，更新_points、_points_update_timestamp、_index_update_timestamp、_xsrf_token字段
        """
        locale.setlocale(locale.LC_ALL, "en_US")
        if SteamGiftsClient.LOGGER is None:
            SteamGiftsClient.LOGGER = logging.getLogger(__name__).getChild(SteamGiftsClient.__name__)
        self._client = RetryClient()
        self._points: int = 0
        self._points_update_timestamp: int = int(time.time())
        self._xsrf_token: str | None = None
        self._index_soup: BeautifulSoup | None = None
        self._load_config_session_id()
        self._load_status()
        self.update_status()
        self.save_status()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_status()
        self._client.close()

    def fetch_giveaways(self, end_timestamp: float = 0.) -> list[Giveaway]:
        """
        从SteamGifts网站获取赠送列表，获取范围是timestamp时间戳之前内结束的赠送；
        :param end_timestamp: 用于确定获取赠送的最晚结束时间
        :return: 赠送列表
        """
        logger = SteamGiftsClient.LOGGER.getChild(self.fetch_giveaways.__name__)
        logger.debug("获取赠送列表")
        giveaway_datas: list[GiveawayData] = []
        page = 1
        last_giveaway_end_timestamp = 0
        # 获取从指定时间以后72小时内结束的赠送
        while last_giveaway_end_timestamp < end_timestamp:
            params = {"format": "json", "page": page}
            response = self._client.get(SteamGiftsClient._GIVEAWAY_LIST_URL, params=params)
            if not response.is_success:
                logger.error("请求赠送列表失败")
                response.raise_for_status()
                break
            data = response.json()
            if not data.get("success"):
                logger.error(f"获取赠送列表失败\n{'-' * 5}响应体{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")
                break
            current_giveaway_datas = data.get("results")
            # 如果当前页没有数据，说明已经过了赠送列表最后一页，应当退出循环
            if not current_giveaway_datas:
                break
            giveaway_datas.extend(current_giveaway_datas)
            page += 1
            last_giveaway_end_timestamp = current_giveaway_datas[-1]["end_timestamp"]
        giveaways: list[Giveaway] = [data2giveaway(data) for data in giveaway_datas]
        logger.debug(f"获取到{len(giveaways)}个赠送")
        return giveaways

    def insert_entry_in_giveaway_details(self, giveaway: Giveaway) -> None:
        """
        在赠送详情页参赠
        :param giveaway: 赠送对象
        """
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(self.insert_entry_in_giveaway_details.__name__)
        name_url = f"<{giveaway.name}> [{giveaway.link}]"
        form_data = {"xsrf_token": self._xsrf_token, "do": "entry_insert", "code": giveaway.code}
        response = self._client.post(SteamGiftsClient._INSERT_DELETE_ENTRY_URL, data=form_data, headers={"Referer": giveaway.link})
        self._common_operations4insert_entry(giveaway, logger, name_url, response)

    def delete_entry_in_giveaway_details(self, giveaway: Giveaway) -> None:
        """
        在赠送详情页退出赠送
        :param giveaway: 赠送对象
        """
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(self.delete_entry_in_giveaway_details.__name__)
        name_url = f"<{giveaway.name}> [{giveaway.link}]"
        form_data = {"xsrf_token": self._xsrf_token, "do": "entry_delete", "code": giveaway.code}
        response = self._client.post(SteamGiftsClient._INSERT_DELETE_ENTRY_URL, data=form_data, headers={"Referer": giveaway.link})
        self._common_operations4delete_entry(giveaway, logger, name_url, response)

    def insert_entry_in_homepage(self, giveaway: Giveaway) -> None:
        """
        在首页参赠
        :param giveaway: 赠送对象
        """
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(self.insert_entry_in_homepage.__name__)
        name_url = f"<{giveaway.name}> [{giveaway.link}]"
        form_data = {"xsrf_token": self._xsrf_token, "do": "entry_insert", "code": giveaway.code}
        response = self._client.post(SteamGiftsClient._INSERT_DELETE_ENTRY_URL, data=form_data, multipart=True)
        self._common_operations4insert_entry(giveaway, logger, name_url, response)

    def delete_entry_in_homepage(self, giveaway: Giveaway) -> None:
        """
        在首页退出赠送
        :param giveaway: 赠送对象
        """
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(self.delete_entry_in_homepage.__name__)
        name_url = f"<{giveaway.name}> [{giveaway.link}]"
        form_data = {"xsrf_token": self._xsrf_token, "do": "entry_delete", "code": giveaway.code}
        response = self._client.post(SteamGiftsClient._INSERT_DELETE_ENTRY_URL, data=form_data, multipart=True)
        self._common_operations4delete_entry(giveaway, logger, name_url, response)

    def _common_operations4insert_entry(self, giveaway: Giveaway, logger: logging.Logger, name_url: str, response: Response):
        """
        解析参赠响应，更新赠送状态，打印相应日志
        :param giveaway: 赠送对象
        :param logger: 日志记录器
        :param name_url: 赠送名称URL
        :param response: 响应对象
        """
        # 参加赠送的响应分类
        # 1. 参加成功
        #    {"type":"success","entry_count":"387","points":"128"}
        # 2. 已参加，参加失败
        #    {"type":"success","points":"128"}
        # 3. 点数不足
        #    {"type":"error","msg":"Not Enough Points","points":"154"}
        # 4. 已赢得相同游戏
        #    {"type":"error","msg":"Previously Won","points":"154"}
        # 5. 游戏已存在于账户中
        #    {"type":"error","msg":"Exists in Account","points":"154"}
        # 6. 赠送已过期
        #    {"type":"error","msg":"Error","points":"154"} 可疑？
        if not response.content:
            logger.warning("csrf_token错误，参赠失败")
            self.update_status()
            return
        data = response.json()
        if data["type"] == "success":
            giveaway.entered = True
            self._common_operation4insert_delete("参加", name_url, giveaway, data, logger)
        elif data["type"] == "error":
            self.points = int(data["points"])
            if (msg := data.get("msg")) == "Not Enough Points":
                logger.warning(f"未能参加{name_url}: 点数不足，当前点数{self.points}，需要{giveaway.points}点数")
            elif msg == "Previously Won":
                logger.info(f"未能参加{name_url}: 之前已赢得此游戏")
            elif msg == "Exists in Account":
                logger.info(f"未能参加{name_url}: 已拥有此游戏")
            elif msg == "Error":
                logger.warning(f"未能参加{name_url}: 赠送过期或删除\n"
                               f"{'-' * 5}响应体开始{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")
            else:
                logger.error(f"未预期的未能参加{name_url}\n{'-' * 5}响应体开始{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")
        else:
            logger.error(f"未预期的未能参加{name_url}\n{'-' * 5}响应体开始{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")

    def _common_operations4delete_entry(self, giveaway: Giveaway, logger: logging.Logger, name_url: str, response: Response):
        """
        解析退赠响应，更新赠送状态，打印相应日志
        :param giveaway: 赠送对象
        :param logger: 日志记录器
        :param name_url: 赠送名称URL
        :param response: 响应对象
        """
        # 退出赠送的响应分类
        # 1. 退出成功
        #    {"type":"success","entry_count":"385","points":"148"}
        # 2. 已退出，退出失败（比退出成功少了entry_count字段）
        #    {"type":"success","points":"148"}
        # 3. 赠送已过期
        #    {"type":"error","msg":"Error","points":"134"} 可疑？
        if not response.content:
            logger.warning("csrf_token错误，退赠失败")
            self.update_status()
            return
        data = response.json()
        if data["type"] == "success":
            giveaway.entered = False
            self._common_operation4insert_delete("退出", name_url, giveaway, data, logger)
        elif data["type"] == "error":
            self.points = int(data["points"])
            logger.warning(f"退出{name_url}失败: 赠送过期或删除\n"
                           f"{'-' * 5}响应体开始{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")
        else:
            logger.error(f"未预期的未能退出{name_url}\n{'-' * 5}响应体开始{'-' * 5}\n{data}\n{'-' * 5}响应体结束{'-' * 5}")

    def _common_operation4insert_delete(self, operation: Literal["参加", "退出"], name_url: str, giveaway: Giveaway,
                                        data: dict[str, Any], logger: logging.Logger):
        self.points = int(data["points"])
        if "entry_count" in data:
            giveaway.entry_count = locale.atoi(data["entry_count"])
            logger.info(f"成功{operation}{name_url}\n剩余点数{self.points:>4d}  Wilson评分{giveaway.wilson_score:>6.3f}  "
                        f"中奖概率{giveaway.winning_probability * 1000:>7.2f}‰  评级{giveaway.rank * 1000:>7.2f}")
        else:
            logger.warning(f"未能{operation}{name_url}: {'已参加' if operation == '参加' else '未参加'}")

    def _load_config_session_id(self):
        """
        1. 从配置文件中读取PHPSESSID到self._client
        2. 如果配置文件中的PHPSESSID无效，则使用之前使用过的PHPSESSID
        3. 如果之前使用过的PHPSESSID无效，则在update_status方法中让用户手动输入PHPSESSID
        """
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(self._load_config_session_id.__name__)
        config = ConfigIO.load()
        phpsessid: str | None = config.get("PHPSESSID")
        old_phpsessid = self._client.get_cookie("PHPSESSID", domain=".www.steamgifts.com", path="/")
        if phpsessid and old_phpsessid!= phpsessid:
            self._client.set_cookie("PHPSESSID", phpsessid, domain=".www.steamgifts.com", path="/")
            if not self._fetch_login_status():
                logger.error(f'{ConfigIO.FILE_PATH}中配置的PHPSESSID: "{phpsessid}"无效')
                if old_phpsessid:
                    self._client.set_cookie("PHPSESSID", old_phpsessid, domain=".www.steamgifts.com", path="/")

    def _load_status(self):
        """从本地文件中读取用户状态，包括积分和xsrf token"""
        status: Status = StatusIO.load()
        self._points = points if (points := status.get("points")) is not None else 0
        self._points_update_timestamp = points_update_timestamp if \
            (points_update_timestamp := status.get("points_update_timestamp")) else int(time.time())
        self._xsrf_token = status.get("xsrf_token")

    def save_status(self):
        if self._xsrf_token is None:
            raise Exception("xsrf_token为空，无法保存状态")
        StatusIO.save_points(self._points, self._points_update_timestamp)
        StatusIO.save_xsrf_token(self._xsrf_token)

    def update_status(self):
        """更新用户状态，包括积分和xsrf token"""
        self._ensure_login()
        self._extract_status()

    def _ensure_login(self):
        logger: logging.Logger = SteamGiftsClient.LOGGER.getChild(SteamGiftsClient._ensure_login.__name__)
        while not self._fetch_login_status():
            logger.warning("尚未登录SteamGifts，请登录")
            self.input_session_cookie()

    def input_session_cookie(self):
        """更新SessionCookie，用于登录SteamGifts网站"""
        session_id = input("请按以下步骤获取并输入PHPSESSID\n"
                           "1. 在浏览器登录SteamGifts网站[https://www.steamgifts.com]\n"
                           "2. 按[F12]键打开浏览器开发者工具\n"
                           "3. 点击[存储]切换到存储页面\n"
                           "4. 点击[Cookie]左侧的三角形以显示网址[https://www.steamgifts.com]\n"
                           "5. 点击网址[https://www.steamgifts.com]将会显示Cookie\n"
                           "6. 复制PHPSESSID右侧的Cookie值并在此处粘贴：")
        while not ConfigIO.validate_phpsessid(session_id):
            session_id = input("SessionId格式不正确，应为48位小写字母、数字的组合，请检查后重新输入：")
        self._client.set_cookie("PHPSESSID", session_id, domain=".www.steamgifts.com", path="/")

    @property
    def login_status(self) -> bool:
        return self._index_soup is not None and self._index_soup.select_one(SteamGiftsClient._LOGIN_SELECTOR) is None

    def _fetch_login_status(self):
        self._index_soup = self._fetch_index_soup()
        return self.login_status

    @property
    def points(self) -> int:
        """
        返回SteamGifts点数
        用户点数每15分钟增长6点，当用户点数大于或等于400时不再增长
        """
        return min(self._points + (int(time.time()) - self._points_update_timestamp) // (15 * 60) * 6, 400)

    @points.setter
    def points(self, points: int):
        self._points: int = points
        self._points_update_timestamp = int(time.time())

    def _fetch_index_soup(self):
        response = self._client.get(SteamGiftsClient._STEAMGIFTS_HOMEPAGE_URL)
        return BeautifulSoup(response.text, "html.parser")

    def _extract_status(self):
        """从首页提取用户状态，包括积分和xsrf token"""
        if self._index_soup is None:
            raise Exception("未获取到首页内容")
        self._xsrf_token = self._extra_xsrf_token(self._index_soup)
        self.points = self._extract_points(self._index_soup)

    @staticmethod
    def _extra_xsrf_token(soup: BeautifulSoup) -> str:
        tag: Tag | None = soup.select_one(SteamGiftsClient._XSRF_SELECTOR)
        if tag is None:
            raise Exception("未在网页中找到xsrf token")
        return str(tag.get("value"))

    @staticmethod
    def _extract_points(soup: BeautifulSoup) -> int:
        tag: Tag | None = soup.select_one(SteamGiftsClient._POINTS_SELECTOR)
        if tag is None:
            raise Exception("未在网页中找到积分")
        return int(tag.text)


if __name__ == "__main__":
    pass

