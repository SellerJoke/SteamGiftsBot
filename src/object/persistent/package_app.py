from sqlalchemy import Table, Column, INTEGER, ForeignKey, PrimaryKeyConstraint, UniqueConstraint

from src.object.persistent.base_entity import Base

# Steam Package和Steam App的多对多关联表
PACKAGE_APP = Table(
    "package_app",
    Base.metadata,
    Column("package_id", INTEGER,
           ForeignKey("steam_package.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    Column("app_id", INTEGER, ForeignKey("steam_app.id", onupdate="CASCADE", ondelete="CASCADE"),
           nullable=False),
    PrimaryKeyConstraint("package_id", "app_id"),
    UniqueConstraint("app_id", "package_id"),
    extend_existing=True,
    comment="steam_package表和steam_app表的多对多关联表",
)
