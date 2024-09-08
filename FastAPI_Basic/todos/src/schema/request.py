from pydantic import BaseModel


class CreateToDoRequest(BaseModel):
    content: str
    is_done: bool

class SignUpRequest(BaseModel):
    username: str
    password: str

class LogInRequest(BaseModel):
    username: str
    password: str