from typing import Any, Iterable, TYPE_CHECKING

from src.object.auxiliary import GiveawayData, UserData, IdName, IdNameDict
from src.object.persistent.base_entity import T
from src.object.persistent.giveaway import Giveaway
from src.object.persistent.steam_app import SteamApp
from src.object.persistent.user import User
if TYPE_CHECKING:
    from src.object.persistent.steam_package import SteamPackage


def data2giveaway(data: GiveawayData) -> Giveaway:
    giveaway = Giveaway(_id=data["id"], name=data["name"], points=data["points"], copies=data["copies"],
                        app_id=data["app_id"], package_id=data["package_id"], link=data["link"],
                        created_timestamp=data["created_timestamp"], start_timestamp=data["start_timestamp"],
                        end_timestamp=data["end_timestamp"], region_restricted=data["region_restricted"],
                        invite_only=data["invite_only"], whitelist=data["whitelist"], group=data["group"],
                        contributor_level=data["contributor_level"], comment_count=data["comment_count"],
                        entry_count=data["entry_count"], creator_id=data["creator"]["id"])
    giveaway.creator = data2user(data["creator"])
    return giveaway


def data2user(data: UserData) -> User:
    return User(id=data["id"], steam_id=data["steam_id"], username=data["username"])


def giveaway2app_info(giveaway: Giveaway) -> IdName:
    assert giveaway.app_id is not None
    return IdName(id=giveaway.app_id, name=giveaway.name)

def giveaway2package_info(giveaway: Giveaway) -> IdName:
    assert giveaway.package_id is not None
    return IdName(id=giveaway.package_id, name=giveaway.name)

def to_id_name(has_id_name: SteamApp | SteamPackage) -> IdName:
    # noinspection PyTypeChecker
    return IdName(id=has_id_name.id, name=has_id_name.name)

def dict2id_name(data: IdNameDict) -> IdName:
    return IdName(id=data["id"], name=data["name"])

def dict_list2id_name_list(data_list: list[IdNameDict]) -> list[IdName]:
    return [dict2id_name(data) for data in data_list]

def entities2dict(entities: Iterable[T]) -> list[dict[str, Any]]:
    """将SQLAlchemy实体类列表转换为字典列表"""
    entities = list(entities)
    if len(entities) == 0:
        return []
    clazz = type(entities[0])
    assert hasattr(clazz, "__table__"), "entities中的元素必须是sqlalchemy.orm.DeclarativeBase的子类"
    result = []
    for entity in entities:
        element = {}
        for column in clazz.__table__.columns:
            value = getattr(entity, column.name)
            if value is None:
                if column.default is not None:
                    if column.default.is_callable:
                        value = column.default.arg(None)
                    elif column.default.is_scalar:
                        value = column.default.arg
                elif column.onupdate is not None:
                    if column.onupdate.is_callable:
                        value = column.onupdate.arg(None)
                    elif column.onupdate.is_scalar:
                        value = column.onupdate.arg
            element[column.name] = value
        result.append(element)
    return result


if __name__ == "__main__":
    pass
