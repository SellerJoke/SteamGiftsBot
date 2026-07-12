from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.object.persistent.package_app import PACKAGE_APP
from src.object.persistent.steam_app import SteamApp
from src.object.persistent.steam_package import SteamPackage
from src.persistence import base_db_io

# 复合数据库操作函数，在此文件中会操作两个或多个表

def merge_packages_by_sqlite(packages: list[SteamPackage], session: Session):
    """
    保存所有SteamPackage到数据库（不存在则新增，存在则更新），且级联保存它关联的SteamApp对象，但是不级联保存它关联的Giveaway对象
    :param packages: SteamPackage可迭代对象
    :param session: 数据库会话
    """
    from sqlalchemy.dialects.sqlite import insert

    if not packages:
        return
    apps: set[SteamApp] = {app for package in packages for app in package.apps}
    relationship_rows = [{"package_id": pkg.id, "app_id": app.id} for pkg in packages for app in pkg.apps]
    package_ids = [pkg.id for pkg in packages]
    base_db_io.merge_all_without_relationship_by_sqlite(apps, session)
    base_db_io.merge_all_without_relationship_by_sqlite(packages, session)
    session.execute(delete(PACKAGE_APP).where(PACKAGE_APP.c.package_id.in_(package_ids)))
    if relationship_rows:
        session.execute(insert(PACKAGE_APP), relationship_rows)
