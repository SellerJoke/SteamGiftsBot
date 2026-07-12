from typing import TypedDict, NamedTuple


class IdName(NamedTuple):
    """定义Steam App和Steam Package信息元组结构（包含id和name）"""
    id: int
    name: str

    def __eq__(self, other):
        return isinstance(other, IdName) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"

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


class Status(TypedDict):
    """定义应用状态字典结构"""
    points: int | None
    points_update_timestamp: int | None
    xsrf_token: str | None


if __name__ == "__main__":
    pass
