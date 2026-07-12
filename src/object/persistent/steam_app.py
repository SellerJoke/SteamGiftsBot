import time
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR, INTEGER, text, BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.object.persistent.base_entity import Base, IntPKMixin, NameMixin
from src.object.persistent.package_app import PACKAGE_APP

if TYPE_CHECKING:
    from src.object.persistent.giveaway import Giveaway
    from src.object.persistent.steam_package import SteamPackage


class SteamApp(Base, IntPKMixin, NameMixin):
    """Steam App实体类"""

    UPDATE_INTERVAL = 7 * 24 * 60 * 60 # App信息更新间隔：7天

    __tablename__ = "steam_app"
    __table_args__ = {'extend_existing': True}
    __mapper_args__ = {'eager_defaults': True}

    # 类别包括game、music、series、video、dlc、mod、hardware、demo、ebook?、tutorial?
    type: Mapped[str | None] = mapped_column(VARCHAR(8))
    total_positive: Mapped[int] = mapped_column(INTEGER, nullable=False)
    total_reviews: Mapped[int] = mapped_column(INTEGER, nullable=False)
    update_timestamp: Mapped[int] = \
        mapped_column(BIGINT, nullable=False, default=lambda : int(time.time()), onupdate=lambda : int(time.time()),
                      server_default=text("strftime('%s', 'now')"), server_onupdate=text("strftime('%s', 'now')"))

    packages: Mapped[list[SteamPackage]] = \
        relationship(secondary=PACKAGE_APP, primaryjoin="SteamApp.id == package_app.c.app_id",
                     secondaryjoin="package_app.c.package_id == SteamPackage.id", back_populates="apps", lazy="noload")
    giveaways: Mapped[list[Giveaway]] = \
        relationship(primaryjoin="Giveaway.app_id == SteamApp.id", cascade="all, delete-orphan", back_populates="app",
                     lazy="noload")

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name}, type={self.type}, "\
               f"total_positive={self.total_positive}, total_reviews={self.total_reviews}, "\
               f"update_timestamp={self.update_timestamp})>"

    @property
    def wilson_score(self) -> float:
        """
        Wilson评分计算函数
        :return: Wilson置信区间的下限
        """
        return SteamApp.wilson_ci(self.total_positive, self.total_reviews)[0]

    @staticmethod
    def wilson_ci(nd: int, n: int, z: float = 1.96) -> tuple[float, float]:
        """
        威尔逊置信区间计算函数
        :param nd: 正例数
        :param n: 总数
        :param z: 正态分布的分位数（查表0.95的置信区间约等于1.96）
        :return: 威尔逊置信区间
        Wilson置信区间的计算公式和代码参考：https://evvail.com/2019/09/21/182.html
        """
        # 如果总数n为0，为方便处理，将Wilson置信区间设定为[0, 0]
        if n == 0:
            return 0, 0
        p = nd * 1. / n * 1.
        z_square = z ** 2
        # Wilson置信区间计算公式的分子中的第1、2个数的和
        numerator1_2 = p + z_square / (2. * n)
        # Wilson置信区间计算公式的分子中的第3个数
        numerator3 = z / (2. * n) * ((4. * n * (1. - p) * p + z_square) ** 0.5)
        # Wilson置信区间计算公式的分母
        denominator = 1. + z_square / n

        low = (numerator1_2 - numerator3) / denominator
        high = (numerator1_2 + numerator3) / denominator

        return low, high

    @property
    def up_to_date(self) -> bool:
        """
        :return: 应用评价信息是否在有效期内
        """
        return time.time() - self.update_timestamp <= SteamApp.UPDATE_INTERVAL


if __name__ == "__main__":
    ubermosh = SteamApp(id=357070, name="UBERMOSH", type="game", total_positive=7304, total_reviews=7956)
    ubermosh3 = SteamApp(id=515570, name="UBERMOSH Vol.3", type="game", total_positive=1363, total_reviews=1492)
    ubermosh5 = SteamApp(id=640380, name="UBERMOSH Vol.5", type="game", total_positive=1456, total_reviews=1549)
    ubermosh7 = SteamApp(id=1029980, name="UBERMOSH Vol.7", type="game", total_positive=418, total_reviews=510)
    ubermosh_soundtrack = SteamApp(id=366420, name="UBERMOSH: Original Soundtrack", type="dlc", total_positive=167, total_reviews=181)
    ubermosh_black = SteamApp(id=1538570, name="UBERMOSH:BLACK", type="game", total_positive=1386, total_reviews=1560)
    ubermosh_omega = SteamApp(id=1181000, name="UBERMOSH:OMEGA", type="game", total_positive=467, total_reviews=518)
    ubermosh_santicide = SteamApp(id=898450, name="UBERMOSH:SANTICIDE", type="game", total_positive=468, total_reviews=525)
    ubermosh_wraith = SteamApp(id=586350, name="UBERMOSH:WRAITH", type="game", total_positive=1373, total_reviews=1492)
    quickerflak = SteamApp(id=1836120, name="QUICKERFLAK", type="game", total_positive=2320, total_reviews=2668)
    trip_2_vinelands = SteamApp(id=546090, name="Trip to Vinelands", type="game", total_positive=1339, total_reviews=1568)
    ttv2 = SteamApp(id=701470, name="TTV2", type="game", total_positive=1259, total_reviews=1454)
    print(ubermosh, ubermosh3, ubermosh5, ubermosh7, ubermosh_soundtrack, ubermosh_black, ubermosh_omega,
          ubermosh_santicide, ubermosh_wraith, quickerflak, trip_2_vinelands, ttv2)
