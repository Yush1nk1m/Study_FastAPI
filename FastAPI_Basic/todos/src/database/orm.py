from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import declarative_base

from schema.request import CreateToDoRequest

Base = declarative_base()

class ToDo(Base):
    __tablename__ = "todo"  # name of table

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(256), nullable=False)
    is_done = Column(Boolean, nullable=False)

    def __repr__(self):
        return f"ToDo(id={self.id}, content={self.content}, is_done={self.is_done}"

    @classmethod
    def create(cls, request: CreateToDoRequest) -> "ToDo":
        return cls(
            content=request.content,
            is_done=request.is_done,
        )

    def done(self) -> "ToDo":
        self.is_done = True
        return self

    def undone(self) -> "ToDo":
        self.is_done = False
        return self