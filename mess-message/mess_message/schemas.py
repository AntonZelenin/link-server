from typing import Optional

from pydantic import BaseModel

from mess_message.helpers import ChatId
from mess_message.models.chat import DBChat


class NewMessage(BaseModel):
    chat_id: int
    sender_id: str
    text: str


class Message(BaseModel):
    chat_id: int
    sender_id: str
    text: str
    is_read: bool
    created_at: float


class NewChat(BaseModel):
    name: Optional[str]
    member_ids: list[str]
    first_message: str


class Chat(BaseModel):
    id: ChatId
    name: Optional[str]
    member_ids: list[str]
    messages: list[Message] = []

    @staticmethod
    async def from_db_chat(db_chat: DBChat) -> 'Chat':
        return Chat(
            id=db_chat.id,
            name=db_chat.name,
            member_ids=[member.user_id for member in await db_chat.awaitable_attrs.chat_members],
            messages=[],
        )


class GetChatResults(BaseModel):
    chats: list[Chat]
