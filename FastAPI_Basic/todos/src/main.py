from fastapi import FastAPI

from api import todo, user

app = FastAPI()
app.include_router(todo.router)
app.include_router(user.router)

@app.get("/", status_code=200)
def health_check_handler():
    return { "ping": "pong" }