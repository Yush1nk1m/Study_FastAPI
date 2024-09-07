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