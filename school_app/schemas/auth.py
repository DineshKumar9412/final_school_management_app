# schemas/auth.py
from pydantic import BaseModel


class WebLoginRequest(BaseModel):
    mobile: str
    password: str