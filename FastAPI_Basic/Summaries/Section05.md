# Section 05. 리팩터링

이번 섹션에서는 기존에 작성한 코드들을 확장성 있게 리팩터링하는 작업을 수행한다.

## FastAPI Router

기존에 작성한 **src/main.py**는 하나의 파일 안에 너무 많은 컨트롤러가 존재했다. 이는 모듈별로 분리할 수 있기 때문에 API Router를 사용해 리팩터링해 보자.

먼저 기존 코드에서 **/todos** URI에 대한 모든 핸들러를 드래그한 후 오른쪽 마우스 클릭 > Refactor > Move 순서로 진행하여 **src/api/todo.py**로 옮겨보자.

**src/api/todo.py**

```
from sys import prefix
from typing import List

from fastapi import Depends, HTTPException, Body, APIRouter
from sqlalchemy.orm import Session

from database.connection import get_db
from database.orm import ToDo
from database.repository import get_todos, get_todo_by_todo_id, create_todo, update_todo, delete_todo
from schema.request import CreateToDoRequest
from schema.response import ToDoListSchema, ToDoSchema

router = APIRouter(prefix="/todos")

@router.get("", status_code=200)
def get_todos_handler(
        order: str | None = None,
        session: Session = Depends(get_db)
) -> ToDoListSchema:
    todos: List[ToDo] = get_todos(session=session)

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
        session: Session = Depends(get_db)
):
    todo: ToDo | None = get_todo_by_todo_id(session=session, todo_id=todo_id)

    if todo:
        return ToDoSchema.model_validate(todo)
    raise HTTPException(status_code=404, detail="To Do Not Found")


@router.post("", status_code=201)
def create_todo_handler(
        request: CreateToDoRequest,
        session: Session = Depends(get_db),
) -> ToDoSchema:
    todo: ToDo = ToDo.create(request=request)   # id = None
    todo: ToDo = create_todo(session=session, todo=todo)    #id = int

    return ToDoSchema.model_validate(todo)


@router.patch("/{todo_id}", status_code=200)
def update_todo_handler(
        todo_id: int,
        is_done: bool = Body(..., embed=True),
        session: Session = Depends(get_db),
):
    todo: ToDo | None = get_todo_by_todo_id(session=session, todo_id=todo_id)
    if todo:
        # update
        todo.done() if is_done else todo.undone()
        todo: ToDo = update_todo(session=session, todo=todo)
        return ToDoSchema.model_validate(todo)
    raise HTTPException(status_code=404, detail="To Do Not Found")


@router.delete("/{todo_id}", status_code=204)
def delete_todo_handler(
        todo_id: int,
        session: Session = Depends(get_db),
):
    todo: ToDo | None = get_todo_by_todo_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="To Do Not Found")

    # delete
    delete_todo(session=session, todo_id=todo_id)
```

그 다음 기존의 코드를 위와 같이 수정한다.

**src/main.py**

```
from fastapi import FastAPI

from api import todo

app = FastAPI()
app.include_router(todo.router)

@app.get("/", status_code=200)
def health_check_handler():
    return { "ping": "pong" }
```

`APIRouter`를 사용하였으므로 기존에 있던 메인 파일에서는 이를 연결시켜주어야 한다. 따라서 위와 같이 `app.include_router()`를 사용해 **/todos** URI에 대한 라우터를 연결해 준다.

**src/tests/test_main.py**

```
from database.orm import ToDo

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == { "ping": "pong" }

def test_get_todos(client, mocker):
    # order=ASC
    mocker.patch("api.todo.get_todos", return_value=[
        ToDo(id=1, content="FastAPI Section 0", is_done=True),
        ToDo(id=2, content="FastAPI Section 1", is_done=False)
    ])
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == {
        "todos": [
            {"id": 1, "content": "FastAPI Section 0", "is_done": True},
            {"id": 2, "content": "FastAPI Section 1", "is_done": False},
        ]
    }

    # order=DESC
    response = client.get("/todos?order=DESC")
    assert response.status_code == 200
    assert response.json() == {
        "todos": [
            {"id": 2, "content": "FastAPI Section 1", "is_done": False},
            {"id": 1, "content": "FastAPI Section 0", "is_done": True},
        ]
    }

def test_get_todo(client, mocker):
    # 200
    mocker.patch(
        "api.todo.get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True),
    )

    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": True,
    }

    # 404
    mocker.patch("api.todo.get_todo_by_todo_id", return_value=None)

    response = client.get("/todos/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}

def test_create_todo(client, mocker):
    create_spy = mocker.spy(ToDo, "create")

    mocker.patch(
        "api.todo.create_todo",
        return_value=ToDo(id=1, content="todo", is_done=True)
    )

    body = {
        "content": "test",
        "is_done": False,
    }
    response = client.post("/todos", json=body)

    assert create_spy.spy_return.id is None
    assert create_spy.spy_return.content == "test"
    assert create_spy.spy_return.is_done == False

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": True,
    }

def test_update_todo(client, mocker):
    # 200
    mocker.patch(
        "api.todo.get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True),
    )
    undone = mocker.patch.object(ToDo, "undone")
    mocker.patch(
        "api.todo.update_todo",
        return_value=ToDo(id=1, content="todo", is_done=False),
    )

    response = client.patch("/todos/1", json={"is_done": False})

    undone.assert_called_once_with()
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": False,
    }

    # 404
    mocker.patch("api.todo.get_todo_by_todo_id", return_value=None)

    response = client.patch("/todos/1", json={"is_done": False})

    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}

def test_delete_todo(client, mocker):
    # 204
    mocker.patch(
        "api.todo.get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True)
    )
    mocker.patch("api.todo.delete_todo", return_value=None)

    response = client.delete("/todos/1")
    assert response.status_code == 204

    # 404
    mocker.patch("api.todo.get_todo_by_todo_id", return_value=None)

    response = client.delete("/todos/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}
```

기존의 테스트 코드에서도 핸들러 함수를 모킹할 때 그 경로를 수정해 준다.

## Dependency Injection & Repository Pattern

의존성이란 어떤 클래스가 기능적으로 다른 클래스를 필요로 하는 것이다. 그리고 의존성 주입이란 이러한 의존성을 클래스가 직접 정의하지 않고 외부에서 전달하는 방식으로 제공하는 것이다.

의존성 주입을 통해 객체 간의 결합도를 낮추고 코드의 유지보수성을 늘릴 수 있다.

이러한 의존성 주입을 활용해 기존에 정의한 리포지토리 패턴을 조금 더 개선해 보자.

**src/database/repository.py**

```
from typing import List

from fastapi import Depends
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from database.connection import get_db
from database.orm import ToDo

class ToDoRepository:
    def __init__(self, session: Session = Depends(get_db)):
        self.session = session

    def get_todos(self) -> List[ToDo]:
        return list(self.session.scalars(select(ToDo)))

    def get_todo_by_todo_id(self, todo_id: int) -> ToDo | None:
        return self.session.scalar(select(ToDo).where(todo_id == ToDo.id))

    def create_todo(self, todo: ToDo) -> ToDo:
        self.session.add(instance=todo)
        self.session.commit()    # db save
        self.session.refresh(instance=todo)  # db read -> determine todo_id
        return todo

    def update_todo(self, todo: ToDo) -> ToDo:
        self.session.add(instance=todo)
        self.session.commit()    # db save
        self.session.refresh(instance=todo)
        return todo

    def delete_todo(self, todo_id: int) -> None:
        self.session.execute(delete(ToDo).where(todo_id == ToDo.id))
        self.session.commit()
```

**/todos** URI에 대한 리포지토리 로직들을 별도의 클래스와 그 안의 메서드들로 구현했다.

**src/api/todo.py**

```
from sys import prefix
from typing import List

from fastapi import Depends, HTTPException, Body, APIRouter

from database.orm import ToDo
from database.repository import ToDoRepository
from schema.request import CreateToDoRequest
from schema.response import ToDoListSchema, ToDoSchema

router = APIRouter(prefix="/todos")

@router.get("", status_code=200)
def get_todos_handler(
        order: str | None = None,
        todo_repo: ToDoRepository = Depends(ToDoRepository),
) -> ToDoListSchema:
    todos: List[ToDo] = todo_repo.get_todos()

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
```

**/todos** 라우터의 로직은 상당히 많은 변경이 있다. 기존엔 세션 객체가 주입되었던 자리에 `Depends(ToDoRepository)`로 리포지토리를 주입했다.

**src/tests/test_main.py**

```
from database.orm import ToDo
from database.repository import ToDoRepository


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == { "ping": "pong" }

def test_get_todos(client, mocker):
    # order=ASC
    mocker.patch.object(ToDoRepository, "get_todos", return_value=[
        ToDo(id=1, content="FastAPI Section 0", is_done=True),
        ToDo(id=2, content="FastAPI Section 1", is_done=False)
    ])
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == {
        "todos": [
            {"id": 1, "content": "FastAPI Section 0", "is_done": True},
            {"id": 2, "content": "FastAPI Section 1", "is_done": False},
        ]
    }

    # order=DESC
    response = client.get("/todos?order=DESC")
    assert response.status_code == 200
    assert response.json() == {
        "todos": [
            {"id": 2, "content": "FastAPI Section 1", "is_done": False},
            {"id": 1, "content": "FastAPI Section 0", "is_done": True},
        ]
    }

def test_get_todo(client, mocker):
    # 200
    mocker.patch.object(
        ToDoRepository,
        "get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True),
    )

    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": True,
    }

    # 404
    mocker.patch.object(ToDoRepository, "get_todo_by_todo_id", return_value=None)

    response = client.get("/todos/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}

def test_create_todo(client, mocker):
    create_spy = mocker.spy(ToDo, "create")

    mocker.patch.object(
        ToDoRepository,
        "create_todo",
        return_value=ToDo(id=1, content="todo", is_done=True)
    )

    body = {
        "content": "test",
        "is_done": False,
    }
    response = client.post("/todos", json=body)

    assert create_spy.spy_return.id is None
    assert create_spy.spy_return.content == "test"
    assert create_spy.spy_return.is_done == False

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": True,
    }

def test_update_todo(client, mocker):
    # 200
    mocker.patch.object(
        ToDoRepository,
        "get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True),
    )
    undone = mocker.patch.object(ToDo, "undone")
    mocker.patch.object(
        ToDoRepository,
        "update_todo",
        return_value=ToDo(id=1, content="todo", is_done=False),
    )

    response = client.patch("/todos/1", json={"is_done": False})

    undone.assert_called_once_with()
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "content": "todo",
        "is_done": False,
    }

    # 404
    mocker.patch.object(ToDoRepository, "get_todo_by_todo_id", return_value=None)

    response = client.patch("/todos/1", json={"is_done": False})

    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}

def test_delete_todo(client, mocker):
    # 204
    mocker.patch.object(
        ToDoRepository,
        "get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True)
    )
    mocker.patch.object(ToDoRepository, "delete_todo", return_value=None)

    response = client.delete("/todos/1")
    assert response.status_code == 204

    # 404
    mocker.patch.object(ToDoRepository, "get_todo_by_todo_id", return_value=None)

    response = client.delete("/todos/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}
```

테스트 코드도 이러한 변경에 따라 `mocker.patch(...)`로 리포지토리 로직을 모킹했던 것을 `mocker.patch.object(ToDoRepository, ...)`와 같이 모킹하게 되었다.
