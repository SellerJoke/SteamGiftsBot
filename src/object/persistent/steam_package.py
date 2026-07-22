from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from src.object.auxiliary import IdName
from src.object.persistent.base_entity import Base, IntPKMixin, NameMixin
from src.object.persistent.package_app import PACKAGE_APP
from src.util.convertor import to_id_name

if TYPE_CHECKING:
    from src.object.persistent.steam_app import SteamApp
    from src.object.persistent.giveaway import Giveaway


class SteamPackage(Base, IntPKMixin, NameMixin):
    """Steam Package实体类"""
    __tablename__ = "steam_package"
    __table_args__ = {'extend_existing': True}

    apps: Mapped[list[SteamApp]] = \
        relationship(secondary=PACKAGE_APP, primaryjoin="SteamPackage.id == package_app.c.package_id",
                     secondaryjoin="package_app.c.app_id == SteamApp.id", back_populates="packages", lazy="selectin")
    giveaways: Mapped[list[Giveaway]] = \
        relationship(primaryjoin="Giveaway.package_id == SteamPackage.id", cascade="all, delete-orphan",
                     back_populates="package", lazy="noload")

    def __init__(self, *, id_: int, name: str, app_infos: list[IdName]):
        super().__init__(id=id_, name=name)
        self._app_infos: list[IdName] = app_infos

    def __repr__(self):
        return f"<{self.__class__.__name__}>(id={self.id}, name={self.name}, app_infos={self.app_infos})>"

    @property
    def app_infos(self) -> list[IdName]:
        """关联的Steam App的id和名字列表"""
        return self._app_infos if hasattr(self, "_app_infos") else [to_id_name(app) for app in self.apps]

    @app_infos.setter
    def app_infos(self, app_infos: list[IdName]):
        self._app_infos = app_infos

    @property
    def wilson_score(self) -> float:
        """
        :return: 关联的游戏的平均威尔逊评分
        """
        game_wilson_scores = [app.wilson_score for app in self.apps if app.type == "game" or app.type is None]
        if len(game_wilson_scores) == 0:
            return 0
        return sum(game_wilson_scores) / len(game_wilson_scores)

    @property
    def fresh(self) -> bool:
        """
        :return: 包内的应用评价信息是否在有效期内
        """
        return all(app.fresh for app in self.apps)


if __name__ == "__main__":
    pass