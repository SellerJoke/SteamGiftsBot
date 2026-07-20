from typing import TypedDict


class IdNameDict(TypedDict):
    """定义Steam App应用信息字典结构"""
    id: int
    name: str

class UserData(TypedDict):
    """定义用户信息字典结构"""
    id: int
    steam_id: str
    username: str


class GiveawayData(TypedDict):
    """定义Giveaway信息字典结构"""
    id: int
    name: str
    points: int
    copies: int
    app_id: int | None
    package_id: int | None
    link: str
    created_timestamp: int
    start_timestamp: int
    end_timestamp: int
    region_restricted: bool
    invite_only: bool
    whitelist: bool
    group: bool
    contributor_level: int
    comment_count: int
    entry_count: int
    creator: UserData