import logging
from typing import Iterable, Any, Literal

from src.object.auxiliary import IdName
# noinspection PyUnusedImports
from src.object.persistent.giveaway import Giveaway
from src.object.persistent.steam_app import SteamApp
from src.object.persistent.steam_package import SteamPackage
# noinspection PyUnusedImports
from src.object.persistent.user import User
from src.requests.non_browser_client import NonBrowserClient
from src.util.convertor import data2id_name_list
from src.util.shared_objects import NON_BROWSER_CLIENT


class SteamClient:
    """与Steam进行请求交互的客户端"""
    LOGGER: logging.Logger = None
    _DETAILS_URLS = {
        "app": "https://store.steampowered.com/api/appdetails",
        "package": "https://store.steampowered.com/api/packagedetails",
    }
    _APP_VIEWS_URL = "https://store.steampowered.com/appreviews/{}"
    _APP_VIEWS_PARAMS = {"json": 1, "num_per_page": 0, "language": "all", "review_type": "all", "purchase_type": "all"}

    def __init__(self):
        if SteamClient.LOGGER is None:
            SteamClient.LOGGER = logging.getLogger(__name__).getChild(SteamClient.__name__)
        self._client: NonBrowserClient = NON_BROWSER_CLIENT

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()

    def fetch_steam_app(self, id_name: IdName) -> SteamApp:
        """
        获取Steam App信息信息
        :param id_name: Steam App ID和名字
        :return: Steam App信息
        """
        logger: logging.Logger = SteamClient.LOGGER.getChild(SteamClient.fetch_steam_app.__name__)
        app_id = id_name.id
        name = id_name.name
        name_id = f"<{name}>[{app_id}]"
        data = self._fetch_details("app", app_id)
        if data:
            app_details = data[str(app_id)]["data"]
            steam_app = SteamApp(id=app_id, name=app_details["name"], type=app_details["type"])
        else:
            steam_app = SteamApp(id=app_id, name=name, available=False)
            logger.warning(f"获取Steam App {name_id}失败：不存在或已删除")

        response = self._client.get(SteamClient._APP_VIEWS_URL.format(app_id), params=SteamClient._APP_VIEWS_PARAMS)
        if response.is_success:
            data = response.json()
            if data["success"] == 1:
                steam_app.total_positive = data["query_summary"]["total_positive"]
                steam_app.total_reviews = data["query_summary"]["total_reviews"]
                logger.info(f"成功获取{steam_app}")
                return steam_app
        steam_app.total_positive = 0
        steam_app.total_reviews = 0
        steam_app.available = False
        logger.warning(f"获取Steam App {name_id}评价失败")
        return steam_app

    def fetch_steam_apps(self, app_infos: Iterable[IdName]) -> list[SteamApp]:
        return [self.fetch_steam_app(app_info) for app_info in app_infos]

    def fetch_steam_package(self, id_name: IdName) -> SteamPackage:
        """
        获取Steam Package信息信息
        :param id_name: Steam Package ID和名字
        :return: Steam Package信息
        """
        logger: logging.Logger = SteamClient.LOGGER.getChild(SteamClient.fetch_steam_package.__name__)
        package_id = id_name.id
        name = id_name.name
        name_id = f"<{name}>[{package_id}]"
        data = self._fetch_details("package", package_id)
        if not data:
            logger.warning(f"获取Steam Package {name_id}失败：不存在或已删除")
            return SteamPackage(id_=package_id, name=name, app_infos=[], available=False)
        package_details = data[str(package_id)]["data"]
        steam_package = SteamPackage(id_=package_id, name=package_details["name"],
                                     app_infos=data2id_name_list(package_details["apps"]))
        logger.info(f"成功获取{steam_package}")
        return steam_package

    def fetch_steam_packages(self, package_infos: Iterable[IdName]) -> list[SteamPackage]:
        return [self.fetch_steam_package(package_info) for package_info in package_infos]

    def _fetch_details(self, category: Literal["app", "package"], id_: int,
                       country_codes: Iterable[str] = ("cn", "hk", "mo", "tw", "sg", "us")) -> dict[str, Any] | None:
        """
        依次使用country_codes中的值作为cc参数和id_参数查询Steam app或package详情，返回第一个成功的响应的json数据，如果不成功则返回None
        :param category: 要查询的Steam信息类别，只能是app或package
        :param id_: 要查询app或package的id
        :param country_codes: 用于切换区域的参数
        :return: Steam API响应的json数据
        """
        if category not in SteamClient._DETAILS_URLS:
            raise ValueError(f"category必须为{list(SteamClient._DETAILS_URLS.keys())}中的一个")
        url = SteamClient._DETAILS_URLS[category]
        params: dict[str, Any] = {f"{category}ids": id_}
        for cc in country_codes:
            params["cc"] = cc
            response = self._client.get(url, params=params)
            if response.is_success:
                data = response.json()
                if data[str(id_)]["success"]:
                    return data
        return None


if __name__ == "__main__":
    pass
