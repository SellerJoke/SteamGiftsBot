import logging
import re
from abc import ABC, abstractmethod

from httpx import Request


# 此文件用于给特定请求提供请求头

class _RequestMatcher(ABC):
    """用于判断请求是否匹配"""

    @abstractmethod
    def match(self, request: Request) -> bool:
        """
        判断当前请求是否匹配
        :param request: 待匹配的请求
        :return: 如果匹配则返回True，否则返回False
        """


class _MethodMatcher(_RequestMatcher):
    """用于判断请求的方法是否匹配"""

    def __init__(self, method: str):
        self.__method = method.upper()

    def match(self, request: Request) -> bool:
        return request.method.upper() == self.__method


class _UrlRegexMatcher(_RequestMatcher):
    """用于判断url是否匹配正则表达式"""

    def __init__(self, url_pattern: str | re.Pattern[str]):
        self.__pattern = url_pattern

    def match(self, request: Request) -> bool:
        url = request.url.host + request.url.path
        if isinstance(self.__pattern, str):
            return url.find(self.__pattern) != -1
        return bool(self.__pattern.search(url))


class _ParamsMatcher(_RequestMatcher):
    """用于判断请求的查询参数是否匹配"""

    def __init__(self, patterns: dict[str, None | str | re.Pattern[str] | list[str | re.Pattern[str]]]):
        self._patterns = patterns

    def match(self, request: Request) -> bool:
        params = request.url.params
        for key, value in self._patterns.items():
            if key not in params:
                return False
            if value is None:
                continue
            for pattern in value if isinstance(value, list) else [value]:
                if isinstance(pattern, str):
                    if params[key] != pattern:
                        return False
                elif isinstance(pattern, re.Pattern):
                    if not pattern.search(params[key]):
                        return False
        return True


class _HeaderMatcher(_RequestMatcher):
    """用于判断请求头是否匹配"""

    def __init__(self, patterns: dict[str, None | str | re.Pattern[str]]):
        self._patterns = patterns

    def match(self, request: Request) -> bool:
        headers = request.headers
        for key, value in self._patterns.items():
            if key not in headers:
                return False
            if value is None:
                continue
            if isinstance(value, str):
                if headers[key] != value:
                    return False
            elif isinstance(value, re.Pattern):
                if not value.search(headers[key]):
                    return False
        return True


class _HeadersPicker:
    """用于根据请求获取对应的请求头"""

    def __init__(self, name: str, headers: dict[str, str], *matchers: _RequestMatcher):
        self.name = name
        self._headers = headers
        self._matchers = matchers

    def match(self, request: Request) -> bool:
        for matcher in self._matchers:
            if not matcher.match(request):
                return False
        return True

    @property
    def headers(self) -> dict[str, str]:
        return self._headers.copy()

    def __str__(self):
        return f"{self.__class__.__name__}[name=({self.name}), headers=({self._headers})]"


class Header:
    """请求头管理类，根据请求获取对应的请求头"""
    LOGGER: logging.Logger = logging.getLogger(__name__).getChild("Header")

    _COMMON_HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
        "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
    }

    _REQUEST_HEADERS_PICKERS = [
        _HeadersPicker(
            "SteamAppDetails",
            {
                # 此请求的响应数据是json类型，但是如果将请求数据类型设为application/json，返回的游戏名可能没有中文，
                # 但请求类型设为text/html可以返回中文游戏名
                # "Accept": "application/json; charset=utf-8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            _MethodMatcher("GET"),
            _UrlRegexMatcher("store.steampowered.com/api/appdetails"),
            _ParamsMatcher({"appids": re.compile(r"^[0-9]{1,30}$")}),
        ),
        _HeadersPicker(
            "SteamRating",
            {
                "Accept": "application/json; charset=utf-8",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            },
            _MethodMatcher("GET"),
            _UrlRegexMatcher(re.compile(r"store\.steampowered\.com/appreviews/[0-9]{1,30}")),
            _ParamsMatcher({"json": "1"}),
        ),
        _HeadersPicker(
            "SteamPackageDetails",
            {
                # 与Steam App请求头类似，这里的Accept设为text/html比较保险（未验证）
                # "Accept": "application/json; charset=utf-8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            },
            _MethodMatcher("GET"),
            _UrlRegexMatcher("store.steampowered.com/api/packagedetails"),
            _ParamsMatcher({"packageids": re.compile(r"^[0-9]{1,30}$")}),
        ),
        _HeadersPicker(
            "SteamGifts-Homepage",
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            _MethodMatcher("GET"),
            _UrlRegexMatcher("www.steamgifts.com"),
        ),
        _HeadersPicker(
            "SteamGifts-Giveaway-JSON-List",
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Priority": "u=0, i",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            _MethodMatcher("GET"),
            _UrlRegexMatcher("www.steamgifts.com/giveaways/search"),
            _ParamsMatcher({"format": "json"}),
        ),
        _HeadersPicker(
            "SteamGiftsEntryOperationInHomepage",
            {
                "Accept": "*/*",
                "Origin": "https://www.steamgifts.com",
                "Priority": "u=0",
                "Referer": "https://www.steamgifts.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            _MethodMatcher("POST"),
            _UrlRegexMatcher("www.steamgifts.com/ajax.php"),
            _HeaderMatcher({"Content-Type": re.compile(r"^multipart/form-data; boundary=")}),
        ),
        _HeadersPicker(
            "SteamGiftsEntryOperationInGiveawayDetail",
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Origin": "https://www.steamgifts.com",
                "Priority": "u=0",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
            },
            _MethodMatcher("POST"),
            _UrlRegexMatcher("www.steamgifts.com/ajax.php"),
            _HeaderMatcher({"Content-Type": re.compile(r"^application/x-www-form-urlencoded")}),
        ),
    ]

    @classmethod
    def universal(cls) -> dict[str, str]:
        """获取适用于所有请求的通用请求头（部分）"""
        return cls._COMMON_HEADERS.copy()

    @classmethod
    def specific_for(cls, request: Request) -> dict[str, str]:
        """获取适用于特定请求的请求头（部分）"""
        for picker in cls._REQUEST_HEADERS_PICKERS:
            if picker.match(request):
                return picker.headers
        cls.LOGGER.getChild(Header.specific_for.__name__).warning(f"未找到与{request}匹配的请求头")
        return {}


if __name__ == "__main__":
    pass
