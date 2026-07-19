import logging
import random
import time

_MODULE_LOGGER: logging.Logger = logging.getLogger(__name__)

class _FrequencyLimit:
	"""用于限制操作频率"""
	def __init__(self, interval: float, max_times: int):
		self.INTERVAL: float = interval
		self.MAX_TIMES: int = max_times
		self.records: list[float] = []

	def add_record(self, visit_time: float):
		self._remove_outdated()
		if len(self.records) >= self.MAX_TIMES:
			raise Exception(f"在{self.INTERVAL}秒内只能执行{self.MAX_TIMES}次操作。时限内最早一次操作的时间是"
							f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.records[0]))}，下一次允许操作的时间"
							f"是{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.records[0] + self.INTERVAL))}，"
							f"当前无法添加操作时间")
		self.records.append(visit_time)

	@property
	def permit_time(self) -> float:
		self._remove_outdated()
		return self.records[0] + self.INTERVAL if len(self.records) >= self.MAX_TIMES else 0

	def _remove_outdated(self):
		current = time.time()
		while self.records and current - self.records[0] > self.INTERVAL:
			self.records.pop(0)


class WebsiteThrottle:
	""""用于限制访问特定域名的节流器"""
	LOGGER: logging.Logger = None

	def __init__(self, domain: str):
		"""
		初始化一个网站节流器
		:param domain: 要限制访问的域名
		"""
		if not WebsiteThrottle.LOGGER:
			WebsiteThrottle.LOGGER = _MODULE_LOGGER.getChild(WebsiteThrottle.__name__)
		self.domain = domain
		self.limits: list[_FrequencyLimit] = []

	def limit(self, interval: float, count: int) -> WebsiteThrottle:
		"""
		添加一个频率限制
		:param interval: 限制时间间隔，单位秒
		:param count: 在此时间间隔内最多能执行的次数
		:return: self
		"""
		self.limits.append(_FrequencyLimit(interval, count))
		return self

	def wait_until_permit(self, url: str):
		"""
		等待直到请求被允许执行
		:param url: 要检查的URL
		"""
		if self.domain in url:
			self.sleep_if_need()

	def record(self, url: str):
		"""
		记录URL请求的时间，只记录与此限制器相关的请求
		:param url: 请求的URL
		"""
		if self.domain in url:
			current_time = time.time()
			for limit in self.limits:
				limit.add_record(current_time)

	def sleep_if_need(self):
		"""如果请求被频率限制，等待直到允许执行"""
		max_permit_time: float = max(limit.permit_time for limit in self.limits)
		if (sleep_interval := max_permit_time - time.time()) > 0:
			WebsiteThrottle.LOGGER.getChild(WebsiteThrottle.sleep_if_need.__name__)\
				.warning(f"请求达到频率限制，等待{sleep_interval:.2f}秒")
			time.sleep(sleep_interval)


def retry_on_exception(exceptions: type[Exception] | tuple[type[Exception], ...], max_time: int = 100,
					   sleep_interval: float = 0.0):
	"""
	装饰器：在指定异常发生时重试
	:param exceptions: 要重试的异常类型列表
	:param max_time: 最大重试次数
	:param sleep_interval: 重试时间间隔，单位秒
	"""
	logger: logging.Logger = _MODULE_LOGGER.getChild(retry_on_exception.__name__)
	def decorator(func):
		def wrapper(*args, **kwargs):
			last_exception: Exception | None = None
			for i in range(max_time):
				try:
					return func(*args, **kwargs)
				except exceptions as e:
					last_exception = e
					if i != max_time - 1:
						logger.error(f"第{i+1}次执行{func.__name__}方法发生异常：{type(e).__name__}({e})")
						if sleep_interval != 0:
							logger.error(f"休眠{sleep_interval:.1f}秒重试")
							time.sleep(sleep_interval)
			raise Exception(f"执行{func.__name__}方法{max_time}次，失败") from last_exception
		return wrapper
	return decorator

def retry_on_502(func):
	"""装饰器：在收到502响应后再次请求，此装饰器仅能应用于返回httpx.Response的函数"""
	max_times = 100
	def wrapper(*args, **kwargs):
		for i in range(max_times):
			response = func(*args, **kwargs)
			if response.status_code != 502:
				return response
		else:
			raise Exception(f"连续收到{max_times}次502响应")
	return wrapper


def delay_random(interval: float | callable = 1):
	"""装饰器：让执行的函数在[0, interval]秒内随机休眠"""
	if callable(interval):
		func1 = interval
		def wrapper1(*args, **kwargs):
			time.sleep(random.uniform(0, 1))
			return func1(*args, **kwargs)
		return wrapper1
	else:
		def decorator(func2):
			def wrapper2(*args, **kwargs):
				time.sleep(random.uniform(0, interval))
				return func2(*args, **kwargs)
			return wrapper2
		return decorator
