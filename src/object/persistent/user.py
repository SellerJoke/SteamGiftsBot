from typing import TYPE_CHECKING

from sqlalchemy import CHAR, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.object.persistent.base_entity import Base, IntPKMixin

if TYPE_CHECKING:
    from src.object.persistent.giveaway import Giveaway

class User(Base, IntPKMixin):
    """用户实体类"""
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    steam_id: Mapped[str] = mapped_column(CHAR(17), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(VARCHAR(255), index=True, nullable=False)

    giveaways: Mapped[list[Giveaway]] = \
        relationship(primaryjoin="Giveaway.creator_id == User.id", cascade="all, delete-orphan", back_populates="creator",
                     order_by="Giveaway.end_timestamp", lazy="noload")

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, steam_id={self.steam_id}, username={self.username})>"


if __name__ == "__main__":
    pass
