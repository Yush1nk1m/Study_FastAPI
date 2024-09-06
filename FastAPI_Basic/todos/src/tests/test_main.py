from database.orm import ToDo

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == { "ping": "pong" }

def test_get_todos(client, mocker):
    # order=ASC
    mocker.patch("main.get_todos", return_value=[
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
        "main.get_todo_by_todo_id",
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
    mocker.patch("main.get_todo_by_todo_id", return_value=None)

    response = client.get("/todos/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}

def test_create_todo(client, mocker):
    create_spy = mocker.spy(ToDo, "create")

    mocker.patch(
        "main.create_todo",
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
        "main.get_todo_by_todo_id",
        return_value=ToDo(id=1, content="todo", is_done=True),
    )
    undone = mocker.patch.object(ToDo, "undone")
    mocker.patch(
        "main.update_todo",
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
    mocker.patch("main.get_todo_by_todo_id", return_value=None)

    response = client.patch("/todos/1", json={"is_done": False})

    assert response.status_code == 404
    assert response.json() == {"detail": "To Do Not Found"}