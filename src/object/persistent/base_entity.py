import time
from typing import TypeVar

from sqlalchemy import INTEGER, VARCHAR, BIGINT, text, BOOLEAN
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    __abstract__ = True


# 下面是SQLAlchemy实体类的常用父类
# 1. 带非自增的INTEGER主键
class IntPKMixin:
    """SQLAlchemy实体类继承此类，可以自动生成主键，主键类型为INTEGER"""
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=False)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self):
        return hash(self.id)


class NameMixin:
    """SQLAlchemy实体类继承此类，添加了name字段"""
    name: Mapped[str] = mapped_column(VARCHAR(255), index=True, nullable=False)


class AvailableMixin:
    """SQLAlchemy实体类继承此类，添加了available字段"""
    available: Mapped[bool] = mapped_column(BOOLEAN, default=True, server_default=text("TRUE"), nullable=False)

    def __init__(self, available: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.available = available if available is not None else True


class UpdateTimestampMixin:
    """SQLAlchemy实体类继承此类，添加了update_timestamp字段"""
    update_timestamp: Mapped[int] = \
        mapped_column(BIGINT, index=True, nullable=False, default=lambda: int(time.time()),
                      onupdate=lambda: int(time.time()),
                      server_default=text("strftime('%s', 'now')"), server_onupdate=text("strftime('%s', 'now')"))

    def __init__(self, update_timestamp: int = None, **kwargs):
        super().__init__(**kwargs)
        self.update_timestamp = update_timestamp if update_timestamp is not None else int(time.time())


T = TypeVar("T", bound=Base)
IntPK = TypeVar("IntPK", bound=IntPKMixin)

if __name__ == '__main__':
    pass