# Section 06. 기능 고도화

## User 모델링

이제 사용자와 todo 간의 관계를 정의하기 위해 `User` ORM을 정의할 것이다.

**src/database/orm.py**

```
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

from schema.request import CreateToDoRequest

Base = declarative_base()

class ToDo(Base):
    __tablename__ = "todo"  # name of table

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String(256), nullable=False)
    is_done = Column(Boolean, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))

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

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(256), nullable=False)
    password = Column(String(256), nullable=False)
```

이렇게 생성하였다면 다음으로는 기존의 데이터베이스에 테이블을 추가하고 빈 컬럼에 값을 넣어 주어야 한다.

```
CREATE TABLE user (
    id INTEGER NOT NULL AUTO_INCREMENT,
    username VARCHAR(256) NOT NULL,
    password VARCHAR(256) NOT NULL,
    PRIMARY KEY (id)
);
ALTER TABLE todo ADD COLUMN user_id INTEGER;
ALTER TABLE todo ADD FOREIGN KEY(user_id) REFERENCES user (id);
INSERT INTO user (username, password) VALUES ("admin", ”password”);
UPDATE todo SET user_id = 1 WHERE id = 1;
SELECT * FROM todo t JOIN user u ON t.user_id = u.id;
```

위와 같은 명령어를 수행해 데이터베이스를 수정하고 잘 수정되었는지 확인해 보자.

## ORM JOIN

이제 생성한 `User` ORM을 불러올 때 Eager loading을 사용하도록 설정해 보고 데이터를 조회해 보자.

**src/database/orm.py**

```
...
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(256), nullable=False)
    password = Column(String(256), nullable=False)
    todos = relationship("ToDo", lazy="joined")
```

`relationship()`의 `lazy="joined"` 옵션을 사용해 Eager loading을 설정하였다. 파이썬 콘솔에서 다음과 같은 명령어를 입력하면 Eager loading이 되고 있음을 확인할 수 있다.

```
>>> from database.orm import User
>>> from sqlalchemy import select
>>> session = SessionFactory()
>>> user = session.scalar(select(User))
>>> user.todos
[ToDo(id=4, content=string, is_done=False, ToDo(id=3, content=FastAPI Section 2, is_done=False, ToDo(id=2, content=FastAPI Section 1, is_done=True, ToDo(id=1, content=FastAPI Section 0, is_done=True]
```

## 회원가입 API 생성 & 비밀번호 암호화(bcrypt)

이번에는 회원가입 API의 스켈레톤 코드만 생성한 후 `bcrypt`로 비밀번호를 해싱하는 방법에 대해 알아보자.

**src/api/user.py**

```
...
@router.post("/sign-up", status_code=201)
def user_sign_up_handler():
    # 1. request body(username, password)
    # 2. password -> hashing -> hashed_password
    # 3. User(username, hashed_password)
    # 4. user -> db save
    # 5. return user(id, username)
    return True
```

이렇게 먼저 로직을 설계해둔 후 일단 True만 반환하도록 스켈레톤 코드를 구성했다.

**src/tests/test_users_api.py**

```
def test_user_sign_up(client):
    response = client.post("/users/sign-up")
    assert response.status_code == 200
    assert response.json() is True
```

테스트 코드도 뼈대만 작성해 두었다. 이 코드가 별도의 파일인 **test_users_api.py**에 작성되었는데, 마찬가지로 기존에 작성했던 **/todos** URI에 대한 API도 별도의 파일로 분리한다.

그 다음으로는 `bcrypt` 패키지를 터미널에서 설치하자.

```
$ pip install bcrypt
```

기본적인 사용 방법은 NestJS와 똑같고 메서드 이름만 다르다.

```
>>> import bcrypt
>>> password = "password"
>>> byte_password = password.encode("UTF-8")
>>> hash_1 = bcrypt.hashpw(byte_password, salt=bcrypt.gensalt())
>>> hash_2 = bcrypt.hashpw(byte_password, salt=bcrypt.gensalt())
>>> bcrypt.checkpw(byte_password, hash_1)
True
>>> bcrypt.checkpw(byte_password, hash_2)
True
```

## 회원가입 API 구현

이번에는 기존에 작성했던 회원가입 API 스켈레톤 코드를 실제로 구현해 보자.

**src/api/user.py**

```
from fastapi import APIRouter, Depends

from database.orm import User
from database.repository import UserRepository
from schema.request import SignUpRequest
from schema.response import UserSchema
from service.user import UserService

router = APIRouter(prefix="/users")

@router.post("/sign-up", status_code=201)
def user_sign_up_handler(
    request: SignUpRequest,
    user_service: UserService = Depends(),
    user_repo: UserRepository = Depends(),
):
    # 1. request body(username, password)
    # 2. password -> hashing -> hashed_password
    hashed_password: str = user_service.hash_password(
        plain_password=request.password,
    )

    # 3. User(username, hashed_password)
    user: User = User.create(
        username=request.username,
        hashed_password=hashed_password
    )

    # 4. user -> db save
    user: User = user_repo.save_user(user=user)

    # 5. return user(id, username)
    return UserSchema.model_validate(user)
```

요청 바디로부터 데이터를 받아 비밀번호를 해싱하고, 사용자 데이터를 생성한 후 DB에 저장하고, 스키마에 맞춰 `model_validate()` 메서드를 적용한 후 반환하는 로직이다.

**src/service/service.py**

```
import bcrypt


class UserService:
    encoding: str = "UTF-8"

    def hash_password(self, plain_password: str) -> str:
        hashed_password: bytes = bcrypt.hashpw(
            plain_password.encode(self.encoding),
            salt=bcrypt.gensalt()
        )
        return hashed_password.decode(self.encoding)
```

서비스 클래스에서는 비밀번호 해싱 메서드를 정의하였다.

**src/database/orm.py**

```
...
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(256), nullable=False)
    password = Column(String(256), nullable=False)
    todos = relationship("ToDo", lazy="joined")

    @classmethod
    def create(cls, username: str, hashed_password: str) -> "User":
        return cls(
            username=username,
            password=hashed_password,
        )
```

ORM에는 사용자 데이터 생성을 위한 클래스 메서드를 정의하였다.

**src/database/repository.py**

```
class UserRepository:
    def __init__(self, session: Session = Depends(get_db)):
        self.session = session

    def save_user(self, user: User) -> User:
        self.session.add(instance=user)
        self.session.commit()
        self.session.refresh(instance=user)
        return user
```

리포지토리 클래스에서는 세션을 의존성 주입받아 DB에 사용자 데이터를 실제로 저장하는 메서드를 정의하였다.

**src/schema/request.py**

```
...
class SignUpRequest(BaseModel):
    username: str
    password: str
```

**src/schema/response.py**

```
...
class UserSchema(BaseModel):
    id: int
    username: str
```

요청과 응답에 대한 스키마는 위와 같다.

요약하자면, 전체적인 로직은 핸들러 함수에서 처리하되 기능과 관련된 세부 로직을 서비스 계층과 리포지토리 계층으로 분리하였다.

## 회원가입 API 테스트

이번에는 구현한 기능에 대한 테스트 코드를 작성해 보자.

**src/tests/test_users_api.py**

```
from database.orm import User
from database.repository import UserRepository
from service.user import UserService


def test_user_sign_up(client, mocker):
    hash_password = mocker.patch.object(
        UserService,
        "hash_password",
        return_value="hashed_password",
    )

    user_create = mocker.patch.object(
        User,
        "create",
        return_value=User(id=None, username="test", password="hashed_password")
    )

    mocker.patch.object(
        UserRepository,
        "save_user",
        return_value=User(id=1, username="test", password="hashed_password"),
    )

    body = {
        "username": "test",
        "password": "password",
    }
    response = client.post("/users/sign-up", json=body)

    hash_password.assert_called_once_with(
        plain_password=body["password"],
    )

    user_create.assert_called_once_with(
        username=body["username"],
        hashed_password="hashed_password",
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "username": "test",
    }
```
