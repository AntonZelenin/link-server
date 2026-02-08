from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    username: str
    password: str


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
