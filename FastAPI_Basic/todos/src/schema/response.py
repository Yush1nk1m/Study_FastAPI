from typing import List

from pydantic import BaseModel, ConfigDict

class ToDoSchema(BaseModel):
    id: int
    content: str
    is_done: bool

    model_config = ConfigDict(
        from_attributes=True
    )

class ToDoListSchema(BaseModel):
    todos: List[ToDoSchema]

class UserSchema(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(
        from_attributes=True
    )
