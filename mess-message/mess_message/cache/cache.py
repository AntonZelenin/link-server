from copy import deepcopy
from typing import Optional

import redis.asyncio as redis
from redis.asyncio.client import Pipeline

from mess_message.helpers import ChatId, UserId
from mess_message.schemas import Message, Chat
from mess_message.settings import get_settings


class Cacher:
    # todo move values to some config/constants?
    CHAT_MESSAGES_EXPIRE = 60 * 60 * 24 * 7
    NUM_OF_MESSAGES_TO_CACHE = 100

    def __init__(self, client: redis.Redis):
        self.client: redis.Redis = client

    async def cache_message(self, message: Message):
        pipe = self.client.pipeline()

        await pipe.rpush(_chat_messages_key(message.chat_id), message.model_dump_json())
        await pipe.ltrim(_chat_messages_key(message.chat_id), -self.NUM_OF_MESSAGES_TO_CACHE, -1)
        await pipe.expire(_chat_messages_key(message.chat_id), self.CHAT_MESSAGES_EXPIRE)

        await pipe.execute()

    async def cache_chat_messages(self, chat: Chat):
        pipe = self.client.pipeline()

        await self._add_chat_messages_to_pipeline(pipe, chat)
        await pipe.execute()

    async def cache_chats_messages(self, chats: list[Chat]):
        pipe = self.client.pipeline()

        for chat in chats:
            await self._add_chat_messages_to_pipeline(pipe, chat)

        await pipe.execute()

    async def _add_chat_messages_to_pipeline(self, pipe: Pipeline, chat: Chat):
        await pipe.rpush(
            _chat_messages_key(chat.id),
            *[message.model_dump_json() for message in chat.messages[-self.NUM_OF_MESSAGES_TO_CACHE:]]
        )
        await pipe.ltrim(_chat_messages_key(chat.id), -self.NUM_OF_MESSAGES_TO_CACHE, -1)
        await pipe.expire(_chat_messages_key(chat.id), self.CHAT_MESSAGES_EXPIRE)

    async def get_chats_messages(self, chat_ids: list[ChatId]) -> dict[ChatId, list[Message]]:
        pipe = self.client.pipeline()
        chat_messages = {}
        for chat_id in chat_ids:
            chat_messages[chat_id] = []
            await pipe.lrange(_chat_messages_key(chat_id), 0, -1)

        res = await pipe.execute()

        for chat_id, messages in zip(chat_ids, res):
            chat_messages[chat_id] = [Message.model_validate_json(message) for message in messages]

        return chat_messages

    async def get_recent_chats(self, user_id: UserId, num_of_chats: int) -> list[Chat]:
        chats_res = await self.client.zrevrange(_user_recent_chats_key(user_id), 0, num_of_chats - 1)
        chats = [Chat.model_validate_json(value) for value in chats_res]

        message_res = await self.get_chats_messages([chat.id for chat in chats])
        for chat in chats:
            # todo what if there are no messages in cache?
            chat.messages = message_res[chat.id]

        return chats

    async def cache_recent_chats(self, user_id: UserId, chats: list[Chat]):
        chats_ = deepcopy(chats)
        await self.cache_chats_messages(chats_)

        pipe = self.client.pipeline()
        for chat in chats_:
            # todo are messages sorted? leave a docstring in repo, in what order
            last_message_created_at = chat.messages[0].created_at
            chat.messages = []
            await pipe.zadd(_user_recent_chats_key(user_id), {chat.model_dump_json(): last_message_created_at})

        await pipe.execute()


def _chat_messages_key(chat_id: ChatId) -> str:
    return f'chat:{chat_id}:messages'


def _user_recent_chats_key(user_id: UserId) -> str:
    return f'user:{user_id}:chats:recent'


class RepositoryContextManager:
    def __init__(self):
        self._repository: Optional[Cacher] = None

    async def __aenter__(self):
        self._repository = await _build_cache_repository()
        return self._repository

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._repository is not None:
            await self._repository.client.aclose()


async def _build_cache_repository() -> Cacher:
    settings = get_settings()
    return Cacher(redis.Redis(
        host=settings.redis_url,
        port=settings.redis_port,
        decode_responses=True,
    ))
