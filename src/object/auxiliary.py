from typing import NamedTuple


class IdName(NamedTuple):
    """定义Steam App和Steam Package信息元组结构（包含id和name）"""
    id: int
    name: str

    def __eq__(self, other):
        return isinstance(other, IdName) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"


if __name__ == "__main__":
    pass
