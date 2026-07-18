import logging
from typing import cast, Iterable, Any

from rich import box
from rich.style import Style
from rich.table import Table
from rich.text import Text
from sqlalchemy import update, insert

from src.object.auxiliary import IdName
from src.object.persistent.giveaway import Giveaway
from src.object.persistent.steam_app import SteamApp
from src.object.persistent.steam_package import SteamPackage
from src.object.persistent.user import User
from src.persistence import giveaway_io, steam_app_io, steam_package_io, composite_db_io, base_db_io
from src.persistence.base_db_io import db_session
from src.requests.steam_client import SteamClient
from src.requests.steamgifts_client import SteamGiftsClient
from src.util.convertor import giveaway2app_info, to_id_name, entities2dict, giveaway2package_info
from src.util.shared_objects import CONSOLE


class Bot:
    """SteamGiftsBot业务实体，此类负责参加/退出赠送的工作流程，包括从Steam获取App信息、从SteamGifts获取赠送信息、参加/退出赠送、更新数据库信息等操作"""
    LOGGER: logging.Logger =  None

    def __init__(self):
        if Bot.LOGGER is None:
            Bot.LOGGER = logging.getLogger(__name__).getChild(Bot.__name__)
        self._steam_client = SteamClient()
        self._steamgifts_client = SteamGiftsClient()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._steam_client.__exit__(exc_type, exc_val, exc_tb)
        self._steamgifts_client.__exit__(exc_type, exc_val, exc_tb)

    def work(self):
        """一轮参加/退出赠送的工作流程"""
        logger: logging.Logger = Bot.LOGGER.getChild(Bot.work.__name__)
        logger.info(f"工作流程开始，SteamGifts点数: {self._steamgifts_client.points}")
        CONSOLE.log(f"开始参加/退出赠送，SteamGifts点数：{self._steamgifts_client.points}")
        # 从数据库获取未结束的赠送列表，按结束时间排序（这也是SteamGifts网站返回的赠送列表的排序方式）
        queried_giveaways: list[Giveaway] = giveaway_io.list_open_giveaways()
        # 从SteamGifts网站获取所有赠送列表
        fetched_giveaways: list[Giveaway] = self._steamgifts_client.fetch_all_giveaways()
        # 合并数据库中查询到的赠送列表和从SteamGifts网站获取到的赠送列表
        all_giveaways = self._merge_and_update_giveaways(queried_giveaways, fetched_giveaways)
        # 根据赠送的评价和中奖概率，参与或退出赠送
        insert_count, delete_count = self.insert_delete_entries(all_giveaways)
        # 把所有赠送和其creator保存到数据库，不保存它关联的SteamApp和SteamPackage，因为在获取新SteamApp和SteamPackage时已经保存过了
        Bot._save_giveaways(fetched_giveaways, queried_giveaways)
        self._steamgifts_client.save_status()
        CONSOLE.log(f"本轮共参加{insert_count}个赠送，退出{delete_count}个赠送")
        logger.info(f"工作流程结束，参加{insert_count}个赠送，退出{delete_count}个赠送")

    def _merge_and_update_giveaways(self, local_giveaways: Iterable[Giveaway], fetched_giveaways: list[Giveaway]) -> list[Giveaway]:
        """
        把从数据库中查询到的仍然开放的赠送列表和从SteamGifts网站获取到赠送列表合并
        如果一个赠送只存在于local_giveaways，不在fetched_giveaways，把此赠送放入最终列表中
        如果一个赠送只存在于fetched_giveaways，不在local_giveaways，从数据库或Steam网站获取该赠送的app、package，把此赠送放入最终列表中
        如果一个赠送同时存在于local_giveaways和fetched_giveaways，使用local_giveaway的entered、app、package字段更新fetched_giveaways，
          丢弃local_giveaway，使用更新后的fetched_giveaway
        :param local_giveaways: 本地收集的赠送列表，包含所有关联对象，但是数据可能过期
        :param fetched_giveaways: 从SteamGifts网站获取到的赠送列表，不包含关联对象
        :return: 合并的更新后的赠送列表
        """
        local_giveaways: dict[int, Giveaway] = {giveaway.id: giveaway for giveaway in local_giveaways}
        fetched_giveaways = fetched_giveaways.copy()
        updated_giveaways: list[Giveaway] = []
        updating_giveaways: list[Giveaway] = []
        while fetched_giveaways:
            fetched_giveaway: Giveaway = fetched_giveaways.pop()
            _id: int = fetched_giveaway.id
            local_giveaway: Giveaway | None = local_giveaways.pop(_id, None)
            if local_giveaway:
                combined_giveaway: Giveaway = Bot._combine_giveaway(local_giveaway, fetched_giveaway)
                if combined_giveaway.rank_up_to_date:
                    updated_giveaways.append(combined_giveaway)
                else:
                    updating_giveaways.append(combined_giveaway)
            else:
                updating_giveaways.append(fetched_giveaway)
        updated_giveaways.extend(filter(lambda giveaway: giveaway.rank_up_to_date, local_giveaways.values()))
        updating_giveaways.extend(filter(lambda giveaway: not giveaway.rank_up_to_date, local_giveaways.values()))
        updated_giveaways.extend(self._update_giveaways(updating_giveaways))
        return updated_giveaways

    @staticmethod
    def _combine_giveaway(local_giveaway: Giveaway, fetched_giveaway: Giveaway) -> Giveaway:
        """合并local_giveaway和fetched_giveaway，返回合并后的giveaway"""
        fetched_giveaway.entered = local_giveaway.entered
        fetched_giveaway.app = local_giveaway.app
        fetched_giveaway.package = local_giveaway.package
        return fetched_giveaway

    def _update_giveaways(self, giveaways: list[Giveaway]) -> list[Giveaway]:
        """
        更新过期的giveaway，返回更新后的giveaway列表
        工作流程
        1. 从giveaways中找到package_id为None且package为None的赠送，收集package_id，从数据库查询package信息
        2. 从giveaways和数据库查询到的package中找到过期的package的id，从Steam网站获取package信息
        3. 从giveaways中找到app_id不为None且app为None的赠送，以及上面从Steam网站获取的package，收集它们的app的id，从数据库查询app信息
        4. 寻找 giveaways中app_id不为None且app为None或过期的app、Steam网站获取的package和数据库中查询到的过期的package的app，
           去掉未过期的app，剩下的就是未查询到或过期的app，收集这些app的id，从Steam网站获取app信息
        5. 合并从数据库中查询到的在有效期内的app和从Steam网站获取到的app
        6. 合并从数据库中查询到的package和从Steam网站获取到的package
        7. 使用合并后的package和app信息更新giveaways
        """
        # 从giveaways中查找要从数据库或Steam获取的package_ids
        querying_package_infos: set[IdName] = {
            giveaway2package_info(giveaway) for giveaway in giveaways
            if giveaway.package_id is not None and giveaway.package is None
        }
        # 用上述package_ids从数据库查询package信息
        queried_packages: list[SteamPackage] = steam_package_io.get_by_ids(info.id for info in querying_package_infos)
        queried_up_to_date_package_infos: set[IdName] = {to_id_name(package) for package in queried_packages if package.up_to_date}
        # 获取giveaways中过期的package_infos
        outdated_giveaway_package_infos: set[IdName] = {
            giveaway2package_info(giveaway) for giveaway in giveaways
            if giveaway.package_id is not None and giveaway.package and not giveaway.package.up_to_date
        }
        # 用待查询package_ids减去已从数据库中查询到的package_ids，得到需要从Steam网站获取的package_ids
        fetching_package_infos: set[IdName] = (querying_package_infos | outdated_giveaway_package_infos) - \
                                              queried_up_to_date_package_infos
        # 从Steam网站获取package信息
        fetched_packages: list[SteamPackage] = self._steam_client.fetch_steam_packages(fetching_package_infos)
        # 从fetched_packages中提取要查询的app信息
        querying_pkg_app_infos: set[IdName] = {app_info for pkg in fetched_packages for app_info in pkg.app_infos}
        # 从giveaways中提取要查询的app信息
        querying_giveaway_app_infos: set[IdName] = {
            giveaway2app_info(giveaway)
            for giveaway in giveaways
            if giveaway.app_id is not None and not giveaway.app
        }
        # 合并querying_pkg_app_infos和querying_giveaway_app_infos，得到需要从数据库或Steam网站获取的app信息
        querying_app_infos: set[IdName] = querying_pkg_app_infos | querying_giveaway_app_infos
        # 用上述app_ids从数据库查询app信息
        queried_up_to_date_apps: list[SteamApp] = steam_app_io.list_by_ids_and_up_to_date(info.id for info in querying_app_infos)
        # 从giveaways中提取过期的app_infos
        outdated_giveaway_app_infos: set[IdName] = {
            giveaway2app_info(giveaway)
            for giveaway in giveaways
            if giveaway.app and not giveaway.app.up_to_date
        }
        # 从giveaways的packages中提取过期的app
        outdated_giveaway_pkg_app_infos: set[IdName] = {
            to_id_name(app)
            for giveaway in giveaways if (pkg := giveaway.package) and not pkg.up_to_date
            for app in cast(SteamPackage, pkg).apps
        }
        # 从queried_packages提取过期的app
        outdated_pkg_app_infos: set[IdName] = {
            to_id_name(app)
            for pkg in queried_packages if not pkg.up_to_date
            for app in pkg.apps
        }
        # 合并querying_app_infos、outdated_giveaway_app_infos、outdated_giveaway_pkg_app_infos、outdated_pkg_app_infos，
        # 移除未过期的，剩下的就是过期的或未查询到的app_info
        fetching_app_infos: set[IdName] = (querying_app_infos | outdated_giveaway_app_infos |
                                           outdated_giveaway_pkg_app_infos | outdated_pkg_app_infos) - \
                                          {to_id_name(app) for app in queried_up_to_date_apps}
        # 从Steam网站获取app信息
        fetched_apps: list[SteamApp] = self._steam_client.fetch_steam_apps(fetching_app_infos)
        # 合并从数据库和Steam网站获取的package和app，使用合并后的package和app信息组装giveaways
        Bot._assemble(giveaways, queried_packages + fetched_packages, queried_up_to_date_apps + fetched_apps)
        Bot._save_fetched_packages_and_apps(fetched_packages, fetched_apps)
        return giveaways

    @staticmethod
    def _assemble(giveaways: Iterable[Giveaway], packages: Iterable[SteamPackage], apps: Iterable[SteamApp]):
        """把SteamApp正确装配到SteamPackage和Giveaway中，把SteamPackage正确装配到Giveaway中"""
        logger: logging.Logger = Bot.LOGGER.getChild(Bot._assemble.__name__)
        packages: dict[int, SteamPackage] = {package.id: package for package in packages}
        apps: dict[int, SteamApp] = {app.id: app for app in apps}
        for giveaway in giveaways:
            if giveaway.package_id is not None and (giveaway.package is None or not giveaway.package.up_to_date):
                package: SteamPackage | None = packages.get(giveaway.package_id)
                if package is None:
                    logger.error(f"未能装配Giveaway，找不到id为{giveaway.package_id}的package")
                    continue
                self_apps: dict[int, SteamApp] = {app.id: app for app in package.apps}
                package.apps = [app for app_info in package.app_infos
                                if (app := (apps.get(app_info.id) or self_apps.get(app_info.id))) is not None]
                giveaway.package = package
            elif giveaway.app_id is not None and (giveaway.app is None or not giveaway.app.up_to_date):
                app: SteamApp | None = apps.get(giveaway.app_id)
                if app is None:
                    logger.error(f"未能装配Giveaway，找不到id为{giveaway.app_id}的app")
                    continue
                giveaway.app = app

    @staticmethod
    def _save_fetched_packages_and_apps(packages: list[SteamPackage], apps: list[SteamApp]):
        """保存从Steam网站获取的package和app到数据库"""
        # Steam网站获取的Steam App要减去SteamPackage中的app，避免重复保存
        saving_apps: set[SteamApp] = set(apps) - {app for pkg in packages for app in pkg.apps}
        with db_session() as session, session.begin():
            base_db_io.merge_all_without_relationship_by_sqlite(saving_apps, session)
            composite_db_io.merge_packages_by_sqlite(packages, session)

    def insert_delete_entries(self, giveaways: list[Giveaway]) -> tuple[int, int]:
        """根据赠送的评级，参加或退出列表中的赠送"""
        # 将赠送按照评级逆序排列，评级越高越值得参加，评级越低越不值得参加
        giveaways.sort(key=lambda giveaway: giveaway.rank, reverse=True)
        # 正数下标：下一个将要参加的赠送的下标
        positive_index: int = 0
        # 负数下标：下一个将要退出的赠送的下标
        negative_index: int = -1
        insert_count: int = 0
        delete_count: int = 0
        table = Bot._create_table()
        while positive_index - negative_index < len(giveaways):
            # 从前往后找到第一个未参加的高评级赠送a
            while positive_index - negative_index < len(giveaways) and giveaways[positive_index].entered:
                positive_index += 1
            # 如果正数下标与负数下标重合还没找到未参加的赠送，说明有价值的赠送已参加完，退出循环
            if (entering_giveaway := giveaways[positive_index]).entered:
                break
            # 如果账户内点数不足以参加赠送，从后往前依次寻找已参加的低评级赠送，退出这些赠送，直到点数足够参加赠送a或负数下标与正数下标重合，退出循环
            while self._steamgifts_client.points < entering_giveaway.points and \
                    positive_index - negative_index < len(giveaways):
                if (quiting_giveaway := giveaways[negative_index]).entered:
                    result: bool = self._steamgifts_client.delete_entry_in_giveaway_details(quiting_giveaway)
                    if result:
                        Bot._add_row(table, quiting_giveaway, self._steamgifts_client.points)
                        delete_count += 1
                negative_index -= 1
            # 如果退出低评级赠送后点数仍不足以参加赠送a，说明所有已参加的赠送的评级均大于未参加的赠送的评级，不用再参赠，退出循环
            if self._steamgifts_client.points < entering_giveaway.points:
                break
            # 如果点数足够，则参加赠送a
            result: bool = self._steamgifts_client.insert_entry_in_giveaway_details(entering_giveaway)
            if result:
                Bot._add_row(table, entering_giveaway, self._steamgifts_client.points)
                insert_count += 1
            # 参加赠送a后，正数下标加1
            positive_index += 1
        CONSOLE.print(table)
        return insert_count, delete_count

    @staticmethod
    def _save_giveaways(fetched_giveaways: list[Giveaway], queried_giveaways: list[Giveaway]):
        """
        保存赠送列表到数据库。
        这里有第二个参数queried_giveaways，是之前从数据库中查询到的旧数据，用于和从网站获取到数据做对比，只保存新增和改变的赠送。
        """
        fetched_giveaways: set[Giveaway] = set(fetched_giveaways)
        queried_giveaways: set[Giveaway] = set(queried_giveaways)
        queried_giveaway_dict: dict[int, Giveaway] = {giveaway.id: giveaway for giveaway in queried_giveaways}
        old_users: dict[int, User] = {giveaway.creator.id: giveaway.creator for giveaway in queried_giveaways}
        # 新增或改变的用户
        new_or_changed_users: set[User] = {
            new for new in {giveaway.creator for giveaway in fetched_giveaways}
            if new.id not in old_users or (old := old_users[new.id]).username != new.username or old.steam_id != new.steam_id
        }
        # 新增赠送
        new_giveaways: set[Giveaway] = fetched_giveaways - queried_giveaways
        # 改变的赠送，因为赠送的字段只有comment_count、entry_count、entered，所以只更新这三个字段
        updating_giveaway_fields: list[dict[str, Any]] = [
            {"id": new.id, "comment_count": new.comment_count, "entry_count": new.entry_count, "entered": new.entered}
            for new in fetched_giveaways
            if (old := queried_giveaway_dict.get(new.id)) and
               (new.comment_count != old.comment_count or new.entry_count != old.entry_count or new.entered != old.entered)
        ]
        # 只存在于数据库而不存在于SteamGifts返回的赠送，用户屏蔽和赢得的游戏赠送都不会出现在SteamGifts返回的赠送列表中
        old_giveaways: set[Giveaway] = queried_giveaways - fetched_giveaways
        old_giveaway_fields: list[dict[str, Any]] = [
            {"id": g.id, "entry_count": g.entry_count, "entered": g.entered} for g in old_giveaways
        ]
        with db_session() as session, session.begin():
            base_db_io.merge_all_without_relationship_by_sqlite(new_or_changed_users, session)
            if new_giveaways:
                session.execute(insert(Giveaway), entities2dict(new_giveaways))
            if updating_giveaway_fields:
                session.execute(update(Giveaway), updating_giveaway_fields)
            if old_giveaway_fields:
                session.execute(update(Giveaway), old_giveaway_fields)

    @staticmethod
    def _create_table() -> Table:
        """初始化要打印的赠送表。"""
        table = Table(title="赠送统计", box=box.SIMPLE)
        table.add_column("赠送ID", width=8)
        table.add_column("游戏名称", max_width=30, justify="left", overflow="fold")
        table.add_column("Wilson score", width=12, justify="right")
        table.add_column("获奖概率", width=9, justify="right")
        table.add_column("评级", max_width=8, justify="right")
        table.add_column("操作", width=4, justify="left")
        table.add_column("剩余点数", max_width=8, justify="right")
        return table

    @staticmethod
    def _add_row(table: Table, giveaway: Giveaway, points: int):
        """添加赠送行到表格。"""
        if giveaway.wilson_score > 0.9:
            score_color = "bright_blue"
        elif giveaway.wilson_score > 0.8:
            score_color = "bright_green"
        elif giveaway.wilson_score > 0.6:
            score_color = "green"
        elif giveaway.wilson_score > 0.4:
            score_color = "yellow"
        else:
            score_color = "red"
        table.add_row(
            str(giveaway.id),
            giveaway.name,
            Text(text=f"{giveaway.wilson_score:>5.3f}", style=Style(color=score_color)),
            f"{giveaway.winning_probability * 1000:>7.2f}‰",
            f"{giveaway.rank * 1000:>7.2f}",
            "参加" if giveaway.entered else "退出",
            f"{points:>3d}"
        )


if __name__ == '__main__':
    pass
