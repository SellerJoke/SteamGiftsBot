import time
from typing import TypeVar, Iterable

from sqlalchemy import BindParameter
from sqlalchemy.sql import roles

from src.object.persistent.steam_app import SteamApp
from src.object.persistent.steam_package import SteamPackage
from src.persistence.base_db_io import db_session

E = TypeVar("E", SteamApp, SteamPackage)


def list_fresh_entities_by_ids(entity_class: type[E], ids: Iterable[int] | BindParameter[int] | roles.InElementRole) \
        -> list[E]:
    """
    从数据库中读取所有在给定ID列表中的实体类记录，且更新时间在最近entity_class.UPDATE_INTERVAL秒内
    :param entity_class: 实体类
    :param ids: 实体类ID列表
    :return: 符合条件的实体类记录列表
    """
    with db_session() as session, session.begin():
        return session.query(entity_class).filter(entity_class.id.in_(ids))\
            .filter(entity_class.update_timestamp > int(time.time()) - entity_class.UPDATE_INTERVAL).all()


if __name__ == "__main__":
    print(list_fresh_entities_by_ids(SteamApp, [1700, 2210, 2270, 2280, 2310, 2800]))
    print(list_fresh_entities_by_ids(SteamPackage, [1334, 6253, 13011]))