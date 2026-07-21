import logging
import time
from typing import Iterable

from src.object.auxiliary import IdName
# noinspection PyUnusedImports
from src.object.persistent.giveaway import Giveaway
from src.object.persistent.steam_app import SteamApp
from src.object.persistent.steam_package import SteamPackage
# noinspection PyUnusedImports
from src.object.persistent.user import User
from src.requests.retry_client import RetryClient
from src.util.convertor import dict_list2id_name_list


class SteamClient:
    """与Steam进行请求交互的客户端"""
    LOGGER: logging.Logger = None
    _APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
    _APP_VIEWS_URL = "https://store.steampowered.com/appreviews/{}"
    _APP_VIEWS_PARAMS = {"json": 1, "num_per_page": 0, "language": "all", "review_type": "all", "purchase_type": "all"}
    _PACKAGE_DETAILS_URL = "https://store.steampowered.com/api/packagedetails?packageids={package_id}&cc={country_code}"

    def __init__(self):
        if SteamClient.LOGGER is None:
            SteamClient.LOGGER = logging.getLogger(__name__).getChild(SteamClient.__name__)
        self._client = RetryClient()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()

    def fetch_steam_app(self, id_name: IdName) -> SteamApp | None:
        """
        获取Steam App信息信息
        :param id_name: Steam App ID和名字
        :return: Steam App信息
        """
        logger: logging.Logger = SteamClient.LOGGER.getChild(SteamClient.fetch_steam_app.__name__)
        _id = id_name.id
        app_id = str(_id)
        name = id_name.name
        name_id = f"<{name}>[{_id}]"
        response = self._client.get(SteamClient._APP_DETAILS_URL, params={"appids": _id})
        if not response.is_success:
            logger.error(f"获取Steam App {name_id}详情失败")
            response.raise_for_status()
            return None
        data = response.json()
        if app_id in data and data[app_id]["success"]:
            app_details = data[app_id]["data"]
            steam_app = SteamApp(id=_id, name=app_details["name"], type=app_details["type"])
        else:
            steam_app = SteamApp(id=_id, name=name)
            logger.warning(f"Steam禁止所在区域访问App {name_id}，详情为空")

        response = self._client.get(SteamClient._APP_VIEWS_URL.format(_id), params=SteamClient._APP_VIEWS_PARAMS)
        if response.is_success:
            data = response.json()
            if data["success"] == 1:
                steam_app.total_positive = data["query_summary"]["total_positive"]
                steam_app.total_reviews = data["query_summary"]["total_reviews"]
                steam_app.update_timestamp = int(time.time())
                logger.info(f"成功获取{steam_app}")
            else:
                steam_app.total_positive = 0
                steam_app.total_reviews = 0
                steam_app.update_timestamp = 0
                logger.warning(f"获取Steam App {name_id}评价失败")
        return steam_app

    def fetch_steam_apps(self, app_infos: Iterable[IdName]) -> list[SteamApp]:
        return [app for app_info in app_infos if (app := self.fetch_steam_app(app_info)) is not None]

    def fetch_steam_package(self, id_name: IdName) -> SteamPackage | None:
        """
        获取Steam Package信息信息
        :param id_name: Steam Package ID和名字
        :return: Steam Package信息
        """
        logger: logging.Logger = SteamClient.LOGGER.getChild(SteamClient.fetch_steam_package.__name__)
        _id = id_name.id
        name = id_name.name
        name_id = f"<{name}>[{_id}]"
        package_id = str(_id)
        # 中国区访问的游戏包信息优先提供中国本地化信息，但有些游戏包信息在中国区不可访问，因此切换到美国区访问
        cn_url = SteamClient._PACKAGE_DETAILS_URL.format(package_id=_id, country_code="cn")
        us_url = SteamClient._PACKAGE_DETAILS_URL.format(package_id=_id, country_code="us")
        should_visit_us_url: bool = False
        response = self._client.get(cn_url)
        if response.is_success:
            data = response.json()
            if not data[package_id]["success"]:
                should_visit_us_url = True
        else:
            should_visit_us_url = True
        if should_visit_us_url:
            response = self._client.get(us_url)
            if not response.is_success:
                logger.error(f"获取Steam Package {name_id}详情失败")
                response.raise_for_status()
                return None
            else:
                data = response.json()
        # noinspection PyUnboundLocalVariable
        if not data[package_id]["success"]:
            logger.warning(f"Steam Package {name_id}已删除，详情为空")
            return SteamPackage(_id=_id, name=name, app_infos=[])
        package_details = data[package_id]["data"]
        steam_package = SteamPackage(_id=_id, name=package_details["name"],
                                     app_infos=dict_list2id_name_list(package_details["apps"]))
        logger.info(f"成功获取{steam_package}")
        return steam_package

    def fetch_steam_packages(self, package_infos: Iterable[IdName]) -> list[SteamPackage]:
        return [package for package_info in package_infos if (package := self.fetch_steam_package(package_info)) is not None]


if __name__ == "__main__":
    pass
