import base64
import logging
import os
import ssl
import tempfile
import time
import typing
from pathlib import Path
from typing import override, Mapping, Sequence

from curl_cffi import CurlOpt
from httpx import Client, Request, Response, URL, ConnectError, USE_CLIENT_DEFAULT, BaseTransport, TimeoutException
# noinspection PyProtectedMember
from httpx._client import UseClientDefault, EventHook
# noinspection PyProtectedMember
from httpx._config import DEFAULT_TIMEOUT_CONFIG, Limits, DEFAULT_LIMITS, DEFAULT_MAX_REDIRECTS
# noinspection PyProtectedMember
from httpx._types import QueryParamTypes, HeaderTypes, CookieTypes, AuthTypes, TimeoutTypes, RequestExtensions, \
    RequestContent, RequestData, RequestFiles, CertTypes, ProxyTypes
from httpx_curl_cffi import CurlTransport

from src.config.config import APP_NAME
from src.persistence.cookie_io import CookieIO
from src.requests.header import Header
from src.requests.meta import WebsiteThrottle, retry_on_exception, retry_on_502
from src.util.file import create_file_if_not_exists


class RetryClient(Client):
    """遭遇特定异常或响应码时，自动重试请求的HTTP Client"""
    LOGGER: logging.Logger = None
    _THROTTLES = [
        WebsiteThrottle("www.steamgifts.com").limit(60, 120) \
            .limit(60 * 60, 2400).limit(60 * 60 * 24, 14400),
        WebsiteThrottle("store.steampowered.com").limit(60, 100).limit(60 * 60, 10000)
    ]
    _PAUSE_SECONDS_429 = 10 * 60
    _PAUSE_SECONDS_502 = 5

    def __init__(self, *, auth: AuthTypes | None = None, params: QueryParamTypes | None = None,
                 headers: HeaderTypes | None = None, cookies: CookieTypes | None = None,
                 verify: ssl.SSLContext | str | bool = True, cert: CertTypes | None = None, trust_env: bool = True,
                 http1: bool = True, http2: bool = False, proxy: ProxyTypes | None = None,
                 mounts: None | (typing.Mapping[str, BaseTransport | None]) = None,
                 timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG, follow_redirects: bool = False,
                 limits: Limits = DEFAULT_LIMITS, max_redirects: int = DEFAULT_MAX_REDIRECTS,
                 event_hooks: None | (typing.Mapping[str, list[EventHook]]) = None, base_url: URL | str = "",
                 transport: BaseTransport | None = None, default_encoding: str | typing.Callable[[bytes], str] = "utf-8"):
        if RetryClient.LOGGER is None:
            RetryClient.LOGGER = logging.getLogger(__name__).getChild(RetryClient.__name__)

        # 下面的操作是将一些默认值合并到参数里
        headers_tmp: dict[str, str] = Header.universal()
        if headers:
            if isinstance(headers, Sequence):
                headers_tmp.update({key: value for key, value in headers})
            elif isinstance(headers, Mapping):
                headers_tmp.update({key: value for key, value in headers.items()})
        headers = headers_tmp

        cookies_tmp = CookieIO.load()
        if cookies:
            cookies_tmp.update(cookies)
        cookies = cookies_tmp

        event_hooks_tmp = {
            "request": [RetryClient._throttle, RetryClient._add_headers],
            "response": [RetryClient._log_status_and_save_cookie],
        }
        if event_hooks:
            event_hooks_tmp = {
                "request": event_hooks_tmp["request"] + event_hooks["request"],
                "response": event_hooks_tmp["response"] + event_hooks["response"],
            }
        event_hooks = event_hooks_tmp

        # impersonate="firefox"：模拟Firefox浏览器的TLS指纹
        # curl_options={CurlOpt.CAINFO: _build_ca_bundle()}：使用系统证书验证网站身份
        transport = transport or \
                    CurlTransport(impersonate="firefox", curl_options={CurlOpt.CAINFO: RetryClient._ca_bundle()})

        super().__init__(auth=auth, params=params, headers=headers, cookies=cookies, verify=verify, cert=cert,
                         trust_env=trust_env, http1=http1, http2=http2, proxy=proxy, mounts=mounts, timeout=timeout,
                         follow_redirects=follow_redirects, limits=limits, max_redirects=max_redirects,
                         event_hooks=event_hooks, base_url=base_url, transport=transport,
                         default_encoding=default_encoding)

    @override
    def close(self) -> None:
        CookieIO.save(super().cookies)
        super().close()

    @override
    @retry_on_502
    @retry_on_exception(exceptions=ConnectError, sleep_interval=20)
    @retry_on_exception(exceptions=TimeoutException)
    def get(self, url: URL | str, *, retry_time: int = 1, params: QueryParamTypes | None = None,
            headers: HeaderTypes | None = None, cookies: CookieTypes | None = None,
            auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
            follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
            timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT, extensions: RequestExtensions | None = None
            ) -> Response:
        """
        重试的get方法
        :param url: 目标url
        :param retry_time: 重试次数
        :param params: url参数
        :param headers: 请求头
        :param cookies: cookies
        :param auth: 认证
        :param follow_redirects: 是否跟随重定向
        :param timeout: 超时时间
        :param extensions: 扩展参数
        :return: 响应对象
        """
        return super().get(url, params=params, headers=headers, cookies=cookies, auth=auth,
                           follow_redirects=follow_redirects, timeout=timeout, extensions=extensions)

    @override
    @retry_on_502
    @retry_on_exception(exceptions=ConnectError, sleep_interval=20)
    @retry_on_exception(exceptions=TimeoutException)
    def post(self, url: URL | str, *, retry_time: int = 1, content: RequestContent | None = None,
             data: RequestData | None = None, multipart: bool = False, files: RequestFiles | None = None, json: typing.Any | None = None,
             params: QueryParamTypes | None = None, headers: HeaderTypes | None = None, cookies: CookieTypes | None = None,
             auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
             follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
             timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT, extensions: RequestExtensions | None = None
             ) -> Response:
        """
        重试的post方法
        :param url:目标url
        :param retry_time: 重试次数
        :param content:
        :param data:
        :param multipart: 是否将data参数编码为供files参数使用的multipart/form-data格式数据
        :param files:
        :param json:
        :param params: url参数
        :param headers: 请求头
        :param cookies: cookies
        :param auth: 认证
        :param follow_redirects: 是否跟随重定向
        :param timeout: 超时时间
        :param extensions: 扩展参数
        :return: 响应对象
        """
        # 如果要将data参数编码为multipart/form-data格式，则将data参数转换为files参数
        if multipart and data is not None and files is None:
            files = RetryClient._to_multipart_files(data)
            data = None
        return super().post(url, content=content, data=data, files=files, json=json, params=params, headers=headers,
                            cookies=cookies, auth=auth, follow_redirects=follow_redirects, timeout=timeout,
                            extensions=extensions)

    def get_cookie(self, name: str, domain: str | None = None, path: str | None = None) -> str | None:
        """获取cookie"""
        return super().cookies.get(name, domain, path)

    def set_cookie(self, name: str, value: str, domain: str = "", path: str = "/"):
        """设置cookie并保存到本地"""
        cookies = super().cookies
        cookies.set(name, value, domain=domain, path=path)
        CookieIO.save(cookies)

    @staticmethod
    def _to_multipart_files(data: Mapping[str, typing.Any]) -> dict[str, tuple[None, typing.Any]]:
        """
        将字典转换为供file参数使用的multipart/form-data格式
        :param data: 输入字典
        :return: 转换后的字典，每个键值对为(None, 厼式化后的值)，用于构建multipart/form-data格式
        """
        return  {k: (None, v) for k, v in data.items()}

    @classmethod
    def _throttle(cls, request: Request):
        url: str = str(request.url)
        for throttle in cls._THROTTLES:
            throttle.wait_until_permit(url)
        for throttle in cls._THROTTLES:
            throttle.record(url)

    @staticmethod
    def _add_headers(request: Request):
        request.headers.update(Header.specific_for(request))

    @classmethod
    def _log_status_and_save_cookie(cls, response: Response):
        logger = cls.LOGGER.getChild(RetryClient._log_status_and_save_cookie.__name__)
        method = response.request.method
        url = str(response.url)
        response.read()
        response_text = f"\n{'-' * 7}响应体{'-' * 7}\n{response.text[:100]}\n{'-' * 7}响应体结束{'-' * 7}" \
            if response.content else ""
        if response.is_success:
            CookieIO.save(response.cookies)
        elif response.status_code == 429:
            logger.error(f"{method} {url} - 429 访问频率过高，已被网站限制访问，休眠{cls._PAUSE_SECONDS_429}秒")
            time.sleep(cls._PAUSE_SECONDS_429)
        elif response.status_code == 502:
            logger.error(f"{method} {url} - 502 休眠{cls._PAUSE_SECONDS_502}秒{response_text}")
            time.sleep(cls._PAUSE_SECONDS_502)
        elif response.status_code == 302:
            logger.info(f"{method} {url} - 302 重定向到{response.url}")
        else:
            logger.error(f"{method} {url} - {response.status_code}{response_text}")
            response.raise_for_status()

    @staticmethod
    def _ca_bundle() -> str:
        pem_path = Path(os.path.join(tempfile.gettempdir(), APP_NAME, "system_ca.pem"))
        if pem_path.is_file() and time.time() - pem_path.stat().st_mtime < 24 * 60 * 60:
            return str(pem_path)
        create_file_if_not_exists(pem_path)
        system_certs = ssl.create_default_context().get_ca_certs(binary_form=True)
        pem_parts = []
        for der in system_certs:
            b64 = base64.b64encode(der).decode("ascii")
            lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
            pem_parts.append("-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----")
        ca_content = "\n\n".join(pem_parts)
        pem_path.write_text(ca_content, encoding="ascii")
        return str(pem_path)

if __name__ == '__main__':
    print([1, 2, 3][: 100])
