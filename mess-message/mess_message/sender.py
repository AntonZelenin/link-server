from typing import Sequence

from mess_message.managers import ConnectionManager
from mess_message.models.chat import ChatMember
from mess_message.schemas import Message


async def send_message(message: Message, chat_members: Sequence[ChatMember], connection_manager: ConnectionManager):
    for member in chat_members:
        if member.user_id != message.sender_id:
            await connection_manager.send_personal_message(member.user_id, message.model_dump_json())

    message.is_read = True
    await connection_manager.send_personal_message(message.sender_id, message.model_dump_json())
