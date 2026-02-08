from typing import Sequence, Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from mess_message.helpers import UserId, ChatId, MessageId
from mess_message.models.chat import Message, DBChat, ChatMember, UnreadMessage


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_message(self, chat_id: int, sender_id: str, text: str) -> Message:
        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        await self.add_to_unread_messages(message)

        return message

    async def add_to_unread_messages(self, message: Message):
        chat_members = (await self.session.scalars(
            select(ChatMember.user_id)
            .where(ChatMember.chat_id == message.chat_id, ChatMember.user_id != message.sender_id)
        )).all()

        self.session.add_all(
            [UnreadMessage(chat_id=message.chat_id, message_id=message.id, user_id=user_id) for user_id in chat_members]
        )
        await self.session.commit()

    async def get_unread_message_ids(self, user_id: UserId, chat_ids: list[ChatId]) -> Sequence[MessageId]:
        return (await self.session.scalars(
            select(UnreadMessage.message_id)
            .where(UnreadMessage.chat_id.in_(chat_ids))
            .where(UnreadMessage.user_id == user_id)
        )).all()

    async def get_messages(self, chat_id: int, number: int = 10) -> Sequence[Message]:
        return (await self.session.scalars(select(Message).where(Message.chat_id == chat_id).limit(number))).all()

    async def chat_exists(self, chat_name: str) -> bool:
        return (await self.session.scalars(select(DBChat).where(DBChat.name == chat_name))).first() is not None

    async def create_chat(self, name: str) -> DBChat:
        chat = DBChat(
            name=name,
        )
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)

        return chat

    async def get_chat(self, chat_id: ChatId) -> Optional[DBChat]:
        return await self.session.scalar(select(DBChat).where(DBChat.id == chat_id))

    async def add_chat_members(self, chat_id: int, member_user_ids: Sequence[str]):
        chat_members = [ChatMember(chat_id=chat_id, user_id=user_id) for user_id in member_user_ids]
        self.session.add_all(chat_members)
        await self.session.commit()

    async def get_chat_members(self, chat_id: int) -> Sequence[ChatMember]:
        return (await self.session.scalars(select(ChatMember).where(ChatMember.chat_id == chat_id))).all()

    async def is_user_in_chat(self, user_id: str, chat_id: int) -> bool:
        return (
            await self.session.scalars(
                select(ChatMember).where(ChatMember.chat_id == chat_id, user_id=user_id))).first() is not None

    async def delete_chat(self, chat_id: int):
        await self.session.execute(
            delete(UnreadMessage).where(UnreadMessage.chat_id == chat_id)
        )
        await self.session.execute(
            delete(Message).where(Message.chat_id == chat_id)
        )
        await self.session.commit()

        await self.session.execute(
            delete(ChatMember).where(ChatMember.chat_id == chat_id)
        )
        await self.session.commit()

        chat = await self.session.scalar(select(DBChat).where(DBChat.id == chat_id))
        await self.session.delete(chat)
        await self.session.commit()

    # it is quite slow btw, it linearly scans all messages
    async def get_recent_user_chats(
            self,
            user_id: UserId,
            exclude_chat_ids: list[ChatId],
            num_of_chats: int = 50,
    ) -> Sequence[DBChat]:
        user_chat_ids_q = select(ChatMember.chat_id).where(ChatMember.user_id == user_id)

        # todo indices?
        recent_chat_ids = (await self.session.execute(
            select(Message.chat_id, func.max(Message.created_at).label('max_created_at'))
            .where(Message.chat_id.in_(user_chat_ids_q))
            .where(Message.chat_id.not_in(exclude_chat_ids))
            .group_by(Message.chat_id)
            .limit(num_of_chats)
        )).scalars().all()

        chat_ids = [chat_id for chat_id in recent_chat_ids]

        result = await self.session.execute(
            # todo I think now it won't work because of greenlet
            select(DBChat).where(DBChat.id.in_(chat_ids))
        )
        return result.scalars().all()

    async def get_chat_messages(self, chat_id: int, num_of_messages: int = 100) -> Sequence[Message]:
        return await self.get_chats_messages([chat_id], num_of_messages)

    async def get_chats_messages(self, chat_ids: list[int], num_of_messages: int = 100) -> Sequence[Message]:
        ranked_messages_subq = (
            select(
                Message.id,
                func.rank().over(
                    partition_by=Message.chat_id,
                    order_by=Message.created_at.asc()
                ).label('rank')
            )
            .where(Message.chat_id.in_(chat_ids))
            .subquery()
        )

        limited_messages_query = (
            select(Message)
            .join(ranked_messages_subq,
                  ranked_messages_subq.c.id == Message.id)
            .where(ranked_messages_subq.c.rank <= num_of_messages)
            .order_by(Message.chat_id, Message.created_at.asc())
        )

        result = await self.session.execute(limited_messages_query)
        return result.scalars().all()

    async def read_all_messages(self, chat_id: int, user_id: str):
        stmt = (
            delete(UnreadMessage)
            .where(
                (UnreadMessage.user_id == user_id) & (UnreadMessage.chat_id == chat_id)
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()
