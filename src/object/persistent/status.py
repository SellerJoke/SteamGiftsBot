from typing import TypedDict


class Status(TypedDict):
    """定义应用状态字典结构"""
    points: int | None
    points_update_timestamp: int | None
    xsrf_token: str | None