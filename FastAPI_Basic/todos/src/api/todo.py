from sys import prefix
from typing import List

from fastapi import Depends, HTTPException, Body, APIRouter

from database.orm import ToDo, User
from database.repository import ToDoRepository, UserRepository
from schema.request import CreateToDoRequest
from schema.response import ToDoListSchema, ToDoSchema
from security import get_access_token
from service.user import UserService

router = APIRouter(prefix="/todos")

@router.get("", status_code=200)
def get_todos_handler(
        access_token = Depends(get_access_token),
        order: str | None = None,
        user_service: UserService = Depends(),
        user_repo: UserRepository = Depends(),
        todo_repo: ToDoRepository = Depends(ToDoRepository),
) -> ToDoListSchema:
    username: str = user_service.decode_jwt(
        access_token=access_token,
    )

    user: User | None = user_repo.get_user_by_username(
        username=username
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    todos: List[ToDo] = user.todos

    if order and order == "DESC":
        return ToDoListSchema(
            todos=[
                ToDoSchema.model_validate(todo)
                for todo in todos[::-1]
            ]
        )
    else:
        return ToDoListSchema(
            todos=[
                ToDoSchema.model_validate(todo)
                for todo in todos
            ]
        )


@router.get("/{todo_id}", status_code=200)
def get_todo_handler(
        todo_id: int,
        todo_repo: ToDoRepository = Depends(ToDoRepository),
):
    todo: ToDo | None = todo_repo.get_todo_by_todo_id(todo_id=todo_id)

    if todo:
        return ToDoSchema.model_validate(todo)
    raise HTTPException(status_code=404, detail="To Do Not Found")


@router.post("", status_code=201)
def create_todo_handler(
        request: CreateToDoRequest,
todo_repo: ToDoRepository = Depends(ToDoRepository),
) -> ToDoSchema:
    todo: ToDo = ToDo.create(request=request)   # id = None
    todo: ToDo = todo_repo.create_todo(todo=todo)    #id = int

    return ToDoSchema.model_validate(todo)


@router.patch("/{todo_id}", status_code=200)
def update_todo_handler(
        todo_id: int,
        is_done: bool = Body(..., embed=True),
        todo_repo: ToDoRepository = Depends(ToDoRepository),
):
    todo: ToDo | None = todo_repo.get_todo_by_todo_id(todo_id=todo_id)
    if todo:
        # update
        todo.done() if is_done else todo.undone()
        todo: ToDo = todo_repo.update_todo(todo=todo)
        return ToDoSchema.model_validate(todo)
    raise HTTPException(status_code=404, detail="To Do Not Found")


@router.delete("/{todo_id}", status_code=204)
def delete_todo_handler(
        todo_id: int,
        todo_repo: ToDoRepository = Depends(ToDoRepository),
):
    todo: ToDo | None = todo_repo.get_todo_by_todo_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="To Do Not Found")

    # delete
    todo_repo.delete_todo(todo_id=todo_id)
