import re
import time
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR, INTEGER, BOOLEAN, ForeignKey, text, BIGINT, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.object.persistent.base_entity import Base, IntPKMixin

if TYPE_CHECKING:
    from src.object.persistent.steam_app import SteamApp
    from src.object.persistent.steam_package import SteamPackage
    from src.object.persistent.user import User


class Giveaway(Base, IntPKMixin):
    """SteamGifts giveaway实体类"""
    __tablename__ = "giveaway"
    __table_args__ = (
        Index("ix_giveaway_entered_endtimestamp", "entered", "end_timestamp"),
        {'extend_existing': True}
    )
    __mapper_args__ = {'eager_defaults': True}

    # 用于从steamgifts链接中提取code
    _CODE_REGEX = re.compile(r"https://www\.steamgifts\.com/giveaway/([a-zA-Z0-9]{5})(/.*)?")
    _PROBABILITY_CONSTANT = 2500

    points: Mapped[int] = mapped_column(INTEGER, default=0, server_default=text("0"), nullable=False)
    copies: Mapped[int] = mapped_column(INTEGER, default=1, server_default=text("1"), nullable=False)
    app_id: Mapped[int | None] = mapped_column(ForeignKey("steam_app.id", onupdate="CASCADE", ondelete="CASCADE"))
    package_id: Mapped[int | None] = mapped_column(ForeignKey("steam_package.id", onupdate="CASCADE", ondelete="CASCADE"))
    link: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    created_timestamp: Mapped[int] = mapped_column(BIGINT, nullable=False)
    start_timestamp: Mapped[int] = mapped_column(BIGINT, nullable=False)
    end_timestamp: Mapped[int] = mapped_column(BIGINT, index=True, nullable=False)
    region_restricted: Mapped[bool] = mapped_column(BOOLEAN, default=False, server_default=text("FALSE"), nullable=False)
    invite_only: Mapped[bool] = mapped_column(BOOLEAN, default=False, server_default=text("FALSE"), nullable=False)
    whitelist: Mapped[bool] = mapped_column(BOOLEAN, default=False, server_default=text("FALSE"), nullable=False)
    group: Mapped[bool] = mapped_column(BOOLEAN, default=False, server_default=text("FALSE"), nullable=False)
    contributor_level: Mapped[int] = mapped_column(INTEGER, default=0, server_default=text("0"), nullable=False)
    comment_count: Mapped[int] = mapped_column(INTEGER, default=0, server_default=text("0"), nullable=False)
    entry_count: Mapped[int] = mapped_column(INTEGER, default=0, server_default=text("0"), nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    entered: Mapped[bool] = mapped_column(BOOLEAN, default=False, server_default=text("FALSE"), nullable=False)

    app: Mapped[SteamApp | None] = relationship(foreign_keys=[app_id], back_populates="giveaways", lazy="joined")
    package: Mapped[SteamPackage | None] = relationship(foreign_keys=[package_id], back_populates="giveaways", lazy="joined")
    creator: Mapped[User] = relationship(foreign_keys=[creator_id], back_populates="giveaways", lazy="joined")

    # noinspection PyShadowingBuiltins
    def __init__(self, *, _id: int, name: str, points: int = 0, copies: int = 1, app_id: int | None = None,
                 package_id: int | None = None, link: str, created_timestamp: int, start_timestamp: int,
                 end_timestamp: int, region_restricted: bool = False, invite_only: bool = False,
                 whitelist: bool = False, group: bool = False, contributor_level: int = 0, comment_count: int = 0,
                 entry_count: int = 0, creator_id: int, entered: bool = False):
        super().__init__(id=_id)
        self._name = name
        self.points = points
        self.copies = copies
        self.app_id = app_id
        self.package_id = package_id
        self.link = link
        self.created_timestamp = created_timestamp
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.region_restricted = region_restricted
        self.invite_only = invite_only
        self.whitelist = whitelist
        self.group = group
        self.contributor_level = contributor_level
        self.comment_count = comment_count
        self.entry_count = entry_count
        self.creator_id = creator_id
        self.entered = entered

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, code={self.code}, name={self.name}, points={self.points}, "\
               f"copies={self.copies}, app_id={self.app_id}, package_id={self.package_id}, link={self.link}, "\
               f"created_timestamp={self.created_timestamp}, start_timestamp={self.start_timestamp}, "\
               f"end_timestamp={self.end_timestamp}, region_restricted={self.region_restricted}, "\
               f"invite_only={self.invite_only}, whitelist={self.whitelist}, group={self.group}, "\
               f"contributor_level={self.contributor_level}, comment_count={self.comment_count}, "\
               f"entry_count={self.entry_count}, creator_id={self.creator_id}, entered={self.entered})>"

    @property
    def name(self) -> str:
        """赠送关联的游戏的名称"""
        if self.app:
            return self.app.name
        elif self.package:
            return self.package.name
        elif hasattr(self, "_name"):
            return self._name
        raise Exception("赠送关联的游戏名称未设置")

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def code(self) -> str:
        """赠送的code，可以唯一确定赠送，此值用于参加或退出赠送"""
        match = Giveaway._CODE_REGEX.match(self.link)
        if not match:
            raise Exception(f"无法从{self.link}中提取code")
        return match.group(1)

    @property
    def wilson_score(self) -> float:
        """赠送的威尔逊评分"""
        return self.app.wilson_score if self.app else self.package.wilson_score if self.package else 0

    @property
    def winning_probability(self) -> float:
        """
        赠送的中奖概率
        计算方法：礼物份数 / 总人数 * 已过时间 / 总时间
        上述计算方法依赖一个假设：参加赠送的总人数与已过时间成正比（此假设并不正确，但勉强能近似表示中奖概率）
        :return: 中奖概率
        """
        if self.entry_count == 0:
            return 1
        result = self.copies / self.entry_count * \
                 (time.time() - self.start_timestamp) / (self.end_timestamp - self.start_timestamp)
        return result if result < 1 else 1

    @property
    def rank(self) -> float:
        """
        赠送评级，用于排序。
        计算公式：(1.26 ^ (wilson_score * 10)) * (winning_probability ^ 0.3)
        如此设计计算公式是为了使wilson_score和winning_probability在各自的取值范围内发生的变化对计算结果有大致相同的影响。
        wilson_score每增加0.1，计算结果会增长1.26倍；
        wilson_score的大致取值范围是[0.15, 0.95]，wilson_score从取值范围的最小值变最大值，增加了0.9，这将导致计算结果增加8倍。
        winning_probability每增长10倍，计算结果大约增长2倍；
        winning_probability的大致取值范围是[1/10000, 1/10]，winning_probability从取值范围的最小值变最大值，
          增长了1000倍，这将导致计算结果增长约8倍。
        :return: 赠送评级
        """
        return (1.26 ** (self.wilson_score * 10)) * (self.winning_probability ** 0.3)

    @property
    def rank_up_to_date(self) -> bool:
        """
        :return: 赠送所关联的Steam App或Steam Package评价信息是否在有效期内
        """
        # 注意，下面的判断使用or运算符连接。
        # 因为一个赠送要么关联一个Steam App，要么关联一个Steam Package，所以app和package中有且只有一个非None值
        return (self.app is not None and self.app.up_to_date) or (self.package is not None and self.package.up_to_date)


if __name__ == "__main__":
    pass



