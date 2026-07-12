from typing import TypeVar

from sqlalchemy import INTEGER, VARCHAR
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    __abstract__ = True


T = TypeVar("T", bound=Base)

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


if __name__ == '__main__':
    pass