from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel

app = FastAPI()

@app.get("/", status_code=200)
def health_check_handler():
    return { "ping": "pong" }

todo_data = {
    1: {
        "id": 1,
        "content": "투두 리스트 내용 1",
        "is_done": True,
    },
    2: {
        "id": 2,
        "content": "투두 리스트 내용 2",
        "is_done": False,
    },
    3: {
        "id": 3,
        "content": "투두 리스트 내용 3",
        "is_done": False,
    },
}

@app.get("/todos", status_code=200)
def get_todos_handler(order: str | None = None):
    ret = list(todo_data.values())
    if order and order == "DESC":
        return ret[::-1]
    else:
        return ret

@app.get("/todos/{todo_id}", status_code=200)
def get_todo_handler(todo_id: int):
    todo = todo_data.get(todo_id)
    if todo:
        return todo
    raise HTTPException(status_code=404, detail="To Do Not Found")

class CreateToDoRequest(BaseModel):
    id: int
    content: str
    is_done: bool

@app.post("/todos", status_code=201)
def create_todo_handler(request: CreateToDoRequest):
    todo_data[request.id] = request.model_dump()
    return todo_data[request.id]

@app.patch("/todos/{todo_id}", status_code=200)
def update_todo_handler(
        todo_id: int,
        is_done: bool = Body(..., embed=True),
):
    todo = todo_data.get(todo_id)
    if (todo):
        todo["is_done"] = is_done
        return todo
    raise HTTPException(status_code=404, detail="To Do Not Found")

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo_handler(todo_id: int):
    todo = todo_data.pop(todo_id, None)
    if todo:
        return
    raise HTTPException(status_code=404, detail="To Do Not Found")