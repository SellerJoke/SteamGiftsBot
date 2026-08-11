from pathlib import Path
from typing import Any, Iterable, Sequence

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.const.path import ROOT_DIR
from src.object.persistent.base_entity import T, Base
# noinspection PyUnusedImports
from src.object.persistent.giveaway import Giveaway
# noinspection PyUnusedImports
from src.object.persistent.package_app import PACKAGE_APP
# noinspection PyUnusedImports
from src.object.persistent.steam_app import SteamApp
# noinspection PyUnusedImports
from src.object.persistent.steam_package import SteamPackage
# noinspection PyUnusedImports
from src.object.persistent.user import User
from src.util.convertor import entities2dict
from src.util.file import create_dir_if_not_exists

_db_path: Path = ROOT_DIR / "resources/persistence/steamgifts_bot.sqlite"
_db_engine = create_engine(f"sqlite:///{_db_path}")


# 设置数据库连接的PRAGMA参数，启用WAL模式和设置busy timeout、同步模式
@event.listens_for(_db_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式
    cursor.execute("PRAGMA synchronous=NORMAL")  # 设置同步模式为NORMAL
    cursor.execute("PRAGMA busy_timeout=5000")  # 设置busy timeout为5秒
    cursor.close()


# 创建数据库session maker，用于创建数据库会话
# 参数expire_on_commit=False：在会话结束后，将结果保留在内存中，而不是再次从数据库中查询（会话结束后再次查询会抛出异常）
_DB_SESSION_MAKER: sessionmaker = sessionmaker(bind=_db_engine, expire_on_commit=False)
create_dir_if_not_exists(_db_path.parent)
Base.metadata.create_all(_db_engine)

# 基础数据库操作函数

def db_session() -> Session:
    """
    创建数据库会话。\n
    每次执行数据库CRUD都应该创建一个数据库会话。
    """
    return _DB_SESSION_MAKER()


def merge_all_without_relationship_by_sqlite(entities: Iterable[T], session: Session = None):
    """
    保存所有实体类到数据库（不存在则新增，存在则更新），不级联保存或更新关联对象
    :param entities: 要保存的实体类
    :param session: 数据库会话
    """
    from sqlalchemy.dialects.sqlite import insert

    entities = entities if isinstance(entities, Sequence) else tuple(entities)
    if not entities:
        return
    clazz = type(entities[0])
    stmt = insert(clazz.__table__)
    pk_columns = [column.name for column in clazz.__table__.primary_key.columns]
    update_columns = {col.name: stmt.excluded[col.name] for col in clazz.__table__.columns if
                      col.name not in pk_columns}
    stmt = stmt.on_conflict_do_update(index_elements=pk_columns, set_=update_columns)
    entity_dicts: list[dict[str, Any]] = entities2dict(entities)
    if session:
        session.execute(stmt, entity_dicts)
    else:
        with db_session() as session, session.begin():
            session.execute(stmt, entity_dicts)


if __name__ == '__main__':
    pass
