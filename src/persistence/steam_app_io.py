import time
from typing import Iterable

from sqlalchemy import BindParameter
from sqlalchemy.sql import roles

from src.object.persistent.steam_app import SteamApp
from src.persistence.base_db_io import db_session


# 提供一些读写SteamApp表的记录的方法

def list_by_ids_and_up_to_date(ids: Iterable[int] | BindParameter[int] | roles.InElementRole) -> list[SteamApp]:
    """
    从数据库中读取所有在给定ID列表中的SteamApp记录，且更新时间在最近SteamApp.UPDATE_INTERVAL秒内
    :param ids: SteamApp ID列表
    :return: 符合条件的SteamApp记录列表
    """
    with db_session() as session, session.begin():
        # noinspection PyTypeChecker
        return session.query(SteamApp).filter(SteamApp.id.in_(ids))\
            .filter(SteamApp.update_timestamp > int(time.time()) - SteamApp.UPDATE_INTERVAL).all()


if __name__ == "__main__":
    pass
