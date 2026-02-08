from pydantic import BaseModel, field_validator

from mess_user.models import user


class UserRegisterData(BaseModel):
    username: str
    password: str

    @field_validator("username", mode="after")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if len(value) < user.USERNAME_MIN_LENGTH or len(value) > user.USERNAME_MAX_LENGTH:
            raise ValueError("Username must be between 3 and 150 characters")
        return value

    @field_validator("password", mode="after")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < user.PASSWORD_MIN_LENGTH or len(value) > user.PASSWORD_MAX_LENGTH:
            raise ValueError("Password must be between 8 and 64 characters")
        return value


class GetUsersByIdsRequest(BaseModel):
    user_ids: list[str]


class SearchUserRequest(BaseModel):
    username: str


class User(BaseModel):
    id: str
    username: str


class SearchUsersResponse(BaseModel):
    users: list[User]
