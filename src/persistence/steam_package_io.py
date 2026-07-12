from typing import Iterable

from sqlalchemy import BindParameter
from sqlalchemy.sql import roles

from src.object.persistent.steam_package import SteamPackage
from src.persistence.base_db_io import db_session

# 提供一些读写SteamPackage表的记录的方法

def get_by_ids(ids: Iterable[int] | BindParameter[int] | roles.InElementRole) -> list[SteamPackage]:
    """
    从数据库中读取所有在给定ID列表中的SteamPackage记录
    :param ids: SteamPackage ID列表
    :return: 符合条件的SteamPackage记录列表
    """
    with db_session() as session, session.begin():
        # noinspection PyTypeChecker
        return session.query(SteamPackage).filter(SteamPackage.id.in_(ids)).all()

if __name__ == "__main__":
    pass
