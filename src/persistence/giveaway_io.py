import time

from sqlalchemy.orm import joinedload

from src.object.persistent.giveaway import Giveaway
from src.object.persistent.steam_package import SteamPackage
from src.persistence.base_db_io import db_session

# 读写数据库中Giveaway表的记录

def list_open_giveaways() -> list[Giveaway]:
    """
    从数据库中读所有未结束的Giveaway记录
    :return: 未结束的Giveaway记录列表
    """
    with db_session() as session, session.begin():
        # noinspection PyTypeChecker
        return session.query(Giveaway)\
            .options(joinedload(Giveaway.app).noload("*"),
                     joinedload(Giveaway.package).selectinload(SteamPackage.apps).noload("*"),
                     joinedload(Giveaway.package).noload(SteamPackage.giveaways),
                     joinedload(Giveaway.creator).noload("*"))\
            .filter(Giveaway.end_timestamp > int(time.time())).all()


if __name__ == "__main__":
    pass
