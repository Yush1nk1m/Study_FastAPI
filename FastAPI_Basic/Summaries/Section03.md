# Section 03. 데이터베이스

## 데이터베이스 기본 설정

실습에서는 MySQL을 데이터베이스로 사용하며 도커를 이용해 설치한다. 따라서 다음과 같은 터미널 명령어로 컨테이너를 생성하고 실행할 수 있다.

```
$ sudo docker run -p 3306:3306 -e MYSQL_ROOT_PASSWORD=todos -e MYSQL_DATABASE=todos -d -v todos:/db --name todos mysql:8.0
$ docker exec -it todos bash
bash-5.1# mysql -u root -p
```

`-v todos:/db` 옵션을 통해 컨테이너가 삭제되더라도 데이터베이스의 데이터가 **/var/lib/docker/volumes/todos/\_data**에 저장되도록 설정하였다. 이제 이 디렉터리는 컨테이너 내부의 **/db** 디렉터리와 동기화된다.

## 데이터베이스와 연결하기

서버에서는 데이터베이스와 연결하고 특정 기능들을 구현하기 위해 `sqlalchemy`, `pymysql`, `cryptography` 라이브러리 설치가 필요하다.

```
$ pip install sqlalchemy
$ pip install pymysql
$ pip install cryptography
```

그 다음 데이터베이스 설정을 위한 디렉터리를 생성하고 파일을 작성하자.

**src/database/connection.py**

```
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+pymysql://root:todos@127.0.0.1:3306/todos"

engine = create_engine(DATABASE_URL, echo=True)
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

SQLAlchemy의 `create_engine` 함수는 데이터베이스와의 연결을 생성한다. 이 엔진을 통해 데이터베이스와 상호작용할 수 있다. `echo=True`는 디버깅용 옵션으로 SQLAlchemy가 실행하는 모든 쿼리를 콘솔에 로깅한다.

`sessionmaker`는 데이터베이스와의 세션을 생성하는 팩토리 함수로, 데이터베이스와의 상호작용을 관리하거나 트랜잭션을 관리하거나 ORM을 통해 데이터에 쿼리를 날릴 수 있다. `autocommit=False` 옵션을 통해 명시적으로 커밋을 해야만 데이터가 저장되도록 설정했고, `autoflush=False` 옵션을 통해 세션이 데이터를 자동으로 플러시하지 않도록 설정했으며, `bind=engine` 옵션으로 이 세션 팩토리를 앞서 생성한 데이터베이스 엔진에 바인딩했다.

## ORM 모델링

FastAPI로 데이터를 모델링하고 ORM 매핑을 해보자.

**src/database/orm.py**

```
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ToDo(Base):
    __tablename__ = "todo"  # name of table

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(256), nullable=False)
    is_done = Column(Boolean, nullable=False)

    def __repr__(self):
        return f"ToDo(id={self.id}, content={self.content}, is_done={self.is_done}"
```

`declarative_base()`로 ORM 클래스의 기본 클래스를 생성하고, 데이터베이스 테이블과 연결된 클래스를 정의할 때 상속하도록 한다.

`__tablename__`에는 해당 클래스가 데이터베이스의 테이블 중 어떤 이름을 가진 테이블과 연결된 것인지 명시한다.

`__repr__()` 메서드는 객체의 문자열 표현을 정의할 수 있다. 이 메서드는 디버깅 시에 유용하며 객체를 출력할 때 어떤 형식으로 표시될지를 결정할 수 있다.

```
ToDo(id=1, content=FastAPI Section 0, is_done=True
ToDo(id=2, content=FastAPI Section 1, is_done=True
ToDo(id=3, content=FastAPI Section 2, is_done=False
```

실제로 데이터베이스 테이블에 있는 데이터들을 하나씩 출력하면 위와 같은 형식을 갖는다.

## ORM 적용 - GET 전체 조회 API와 리포지토리 패턴

이제 ORM을 적용해 메모리 기반으로 생성하였던 API를 하나씩 수정해 나갈 것이다.

**src/database/connection.py**

```
...
def get_db():
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
```

먼저 제너레이터 패턴을 사용해 `get_db()`라는 함수를 정의한다. 이는 팩토리 패턴으로 만들어진 데이터베이스 세션을 반환하고, caller가 해당 세션을 모두 이용한 후 종료하면 다시 돌아와 finally 블록을 수행해 세션을 닫는다. 이는 FastAPI를 사용해 데이터베이스 작업을 수행할 때에 있어 매우 중요한 패턴이다.

**src/database/repository.py**

```
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.orm import ToDo

def get_todos(session: Session) -> List[ToDo]:
    return list(session.scalars(select(ToDo)))
```

이는 리포지토리 패턴을 사용해 데이터베이스 작업을 별도의 파일로 분리한 것이다. 파이썬의 타이핑 문법을 사용해 코드 가독성이 높아졌다.

**src/main.py**

```
from typing import List

from fastapi import FastAPI, Body, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.orm import ToDo
from database.repository import get_todos
...
@app.get("/todos", status_code=200)
def get_todos_handler(
        order: str | None = None,
        session: Session = Depends(get_db)
):
    todos: List[ToDo] = get_todos(session=session)

    if order and order == "DESC":
        return todos[::-1]
    else:
        return todos
```

원래는 오름차순, 내림차순 정렬도 DB 로직에서 담당해야 하지만 지금은 임시적으로 해당 부분은 생략하고 핸들러 함수에서 세션을 관리하는 과정만 주의깊게 보도록 한다.

핸들러 함수의 매개변수로 데이터베이스 세션을 의존성 주입받아 사용한다. 앞서 리포지토리에서 정의한 `get_todos()` 함수에 세션을 전달하여 데이터를 받아오고 반환하는 간단한 로직이다.

이 코드들에서 중요하게 보아야 할 것은 데이터베이스 조작을 위해 리포지토리 패턴을 분리한 점, 그리고 제너레이터 패턴을 사용하여 세션을 안전하게 관리한 점이다.

## ORM 적용 - HTTP Response 처리와 스키마

FastAPI에서는 DTO 대신 Schema라는 표현을 사용한다. 이번에는 응답 형식을 JSON으로 안전하게 변환하기 위한 스키마를 정의할 것이다.

**src/schema/response.py**

```
from typing import List

from pydantic import BaseModel

class ToDoSchema(BaseModel):
    id: int
    content: str
    is_done: bool

    class Config:
        from_attributes = True

class ListToDoResponse(BaseModel):
    todos: List[ToDoSchema]
```

이렇게 정의한 후엔 파이썬 콘솔을 통해 실제로 이 스키마를 사용할 수 있는지 검증해 보자.

```
>>> from schema.response import ToDoSchema
>>> from database.orm import ToDo
>>> todo = ToDo(id=100, content="test", is_done=True)
>>> ToDoSchema.model_validate(todo)
ToDoSchema(id=100, content='test', is_done=True)
```

pydantic의 `BaseModel`을 상속받은 클래스에는 `model_validate()`라는 메서드가 존재한다. 내부 클래스인 `Config`에서 `from_attributes = True`로 설정하여 ORM 객체로부터 데이터를 변환할 수 있다.

이제 이것을 앞서 리팩터링한 `get_todos_handler()` 함수의 데이터 반환 부분에 적용해 보자.

**src/main.py**

```
...
@app.get("/todos", status_code=200)
def get_todos_handler(
        order: str | None = None,
        session: Session = Depends(get_db)
) -> ListToDoResponse:
    todos: List[ToDo] = get_todos(session=session)

    if order and order == "DESC":
        return ListToDoResponse(
            todos=[
                ToDoSchema.model_validate(todo)
                for todo in todos[::-1]
            ]
        )
    else:
        return ListToDoResponse(
            todos=[
                ToDoSchema.model_validate(todo)
                for todo in todos
            ]
        )
```

파이썬의 list comprehension 문법을 사용해 todos의 각각의 데이터를 `model_validate()` 메서드를 적용해 JSON 데이터로 직렬화한다.

## ORM 적용 - GET 단일 조회 API

이번엔 단일한 todo를 조회하는 API에 ORM을 적용할 것이다. 먼저 리포지토리에 다음과 같은 함수를 정의한다.

**src/database/repository.py**

```
def get_todo_by_todo_id(session: Session, todo_id: int) -> ToDo | None:
    return session.scalar(select(ToDo).where(todo_id == ToDo.id))
```

그리고 핸들러 함수를 다음과 같이 변경한다.

**src/main.py**

```
@app.get("/todos/{todo_id}", status_code=200)
def get_todo_handler(
        todo_id: int,
        session: Session = Depends(get_db)
):
    todo: ToDo | None = get_todo_by_todo_id(session=session, todo_id=todo_id)

    if todo:
        return ToDoSchema.model_validate(todo)
    raise HTTPException(status_code=404, detail="To Do Not Found")
```

리포지토리 패턴을 사용하여 데이터베이스 조회 로직을 분리하고 핸들러 함수에서는 세션 객체만 전달하도록 했다는 점에서 전체 조회 API와 큰 흐름은 같지만, 이 코드는 추가적으로 쿼리를 날릴 때 where 옵션을 어떻게 명시하는지를 나타내고 있다.

## Refactoring

이번에는 PyCharm의 강력한 리팩터링 기능을 사용해 기존 코드를 일부 수정해볼 것이다.

![Refactor](Images/image3.png)

먼저 기존에 **src/main.py**에 있던 `CreateToDoRequest` 스키마를 **src/schema/request.py**로 이동하고, **src/schema/response.py**에 있었던 `ListToDoResponse` 스키마의 이름을 `ToDoListSchema`로 변경한다. 이렇게 하면 코스트 없이 해당 스키마들을 불러오는 파일들이 자동적으로 수정된다.

## ORM 적용 - POST API

이번에는 기존의 POST API에 데이터베이스를 적용해 보자.

**src/database/orm.py**

```
...
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
```

먼저 데이터베이스 테이블에 매핑된 `ToDo` 클래스에 `create()` 메서드를 정의하여 팩토리 패턴으로 주어진 데이터를 `ToDo` 객체로 변환하여 생성해 주는 역할을 한다.

**src/database/repository.py**

```
def create_todo(session: Session, todo: ToDo) -> ToDo:
    session.add(instance=todo)
    session.commit()    # db save
    session.refresh(instance=todo)  # db read -> determine todo_id
    return todo
```

그리고 리포지토리에서는 todo를 실제로 생성하는 로직을 처리하는 함수를 별도로 정의한다. 이때 앞서 데이터베이스 설정 시 `autocommit=False` 옵션을 전달했기 때문에 `session.commit()`으로 명시적으로 커밋하여 데이터베이스에 새로운 데이터가 저장되도록 한 점에 주목하자. 그 이후 `session.refresh()`로 데이터베이스에 저장된 데이터를 다시 읽어와 todo 변수에 저장하고 반환한다.

**src/schema/request.py**

```
from pydantic import BaseModel


class CreateToDoRequest(BaseModel):
    content: str
    is_done: bool

```

그리고 앞서 메모리 기반으로 구현할 때는 id가 자동 부여되지 않아 스키마에 id를 포함했었는데, 이제는 데이터베이스가 자동적으로 부여해주므로 id 필드를 제거한다.

**src/main.py**

```
@app.post("/todos", status_code=201)
def create_todo_handler(
        request: CreateToDoRequest,
        session: Session = Depends(get_db),
) -> ToDoSchema:
    todo: ToDo = ToDo.create(request=request)   # id = None
    todo: ToDo = create_todo(session=session, todo=todo)    #id = int

    return ToDoSchema.model_validate(todo)
```

최종적으로 ORM이 적용된 핸들러 함수는 위와 같다. 요청 스키마를 `ToDo` 클래스의 내장 메서드로 전달해 ORM 객체로 변환하고, 이를 세션과 함께 리포지토리 함수에 전달해 데이터베이스에 실제로 저장한다. 그리고 그 결과를 스키마의 `model_validate()` 메서드를 사용해 직렬화하여 클라이언트에게 반환하는 구조이다.

## ORM 적용 - PATCH API

이번에는 PATCH API에 ORM을 적용해볼 것이다.

**src/database/orm.py**

```
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
```

먼저 `ToDo` 클래스에 `done()`, `undone()`이라는 메서드를 정의한다. 이는 `ToDo` 객체를 전달받아 그 객체의 `is_done` 속성을 조작하는 메서드인데, 이렇게 setter를 별도로 정의함으로써 객체지향 원리에 맞추어 유지보수성이 좋은 코드를 작성할 수 있다.

**src/database/repository.py**

```
...
def create_todo(session: Session, todo: ToDo) -> ToDo:
    session.add(instance=todo)
    session.commit()    # db save
    session.refresh(instance=todo)  # db read -> determine todo_id
    return todo

def update_todo(session: Session, todo: ToDo) -> ToDo:
    session.add(instance=todo)
    session.commit()    # db save
    session.refresh(instance=todo)
    return todo
```

리포지토리 패턴에서 특이한 점은 `update_todo()` 함수가 `create_todo()` 함수와 완전히 똑같은 로직이라는 것이다. 이 역시 유지보수성을 고려한 것으로 단일 책임 원칙에 맞추어 함수를 설계하는 것이 적합하다.

**src/main.py**

```
@app.patch("/todos/{todo_id}", status_code=200)
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
```

삼항 연산자와 객체 내장 메서드를 사용해 유지 보수성 좋게 핸들러 함수에 ORM을 적용하였다.

## ORM 적용 - DELETE API

마지막으로 DELETE API에 ORM을 적용해 보자.

**src/database/repository.py**

```
def delete_todo(session: Session, todo_id: int) -> None:
    session.execute(delete(ToDo).where(todo_id == ToDo.id))
    session.commit()
```

`select()`는 `session.scalar()` 또는 `session.scalars()`를 통해 호출했다면, `delete()`는 `session.execute()`를 통해 호출해야 한다. 그리고 명시적으로 커밋해 주는 것에 주의하자.

**src/main.py**

```
@app.delete("/todos/{todo_id}", status_code=204)
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

이렇게 메모리 기반으로 구현한 CRUD 기능들을 모두 ORM을 적용하여 변경해 보았다.
