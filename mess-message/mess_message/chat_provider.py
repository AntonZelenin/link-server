from mess_message import schemas
from mess_message.cache.cache import Cacher
from mess_message.helpers import UserId
from mess_message.models.chat import DBChat
from mess_message.repository import Repository
from mess_message.schemas import Chat
from mess_message.settings import get_settings


# get chats from cache
# get everything earlier and if less than N chats, get the rest from db
# cache everything that is not in the cache
# transform
# return
# on a new message update key in cache, update chat ttl, cache the message


class ChatProvider:
    def __init__(self, repository: Repository, cacher: Cacher):
        self.repository = repository
        self.cacher = cacher
        self.settings = get_settings()

    async def get_recent_chats(self, user_id: UserId) -> list[Chat]:
        recent_cached_chats = await self.cacher.get_recent_chats(user_id, self.settings.num_of_chats_to_per_page)
        recent_uncached_chats = []

        # todo for now it doesn't load chats that are earlier than the last cached chat
        # todo so in case caching is not working properly, it will not load the newest chats
        if len(recent_cached_chats) < self.settings.num_of_chats_to_per_page:
            recent_db_chats = list(
                await self.repository.get_recent_user_chats(
                    user_id,
                    [chat.id for chat in recent_cached_chats],
                    self.settings.num_of_chats_to_per_page),
            )

            if recent_db_chats:
                recent_db_chat_ids = [chat.id for chat in recent_db_chats]
                messages = await self.repository.get_chats_messages(recent_db_chat_ids)
                unread_messages = await self.repository.get_unread_message_ids(user_id, recent_db_chat_ids)

                recent_uncached_chats = await self._build_db_chats(recent_db_chats, messages, unread_messages)

                # todo probably it should be done via a message queue
                await self.cacher.cache_recent_chats(user_id, recent_uncached_chats)

        recent_cached_chats.extend(recent_uncached_chats)
        return recent_cached_chats

    @staticmethod
    async def _build_db_chats(recent_db_chats: list[DBChat], messages, unread_messages) -> list[Chat]:
        db_chats = {db_chat.id: await Chat.from_db_chat(db_chat) for db_chat in recent_db_chats}
        for message in messages:
            db_chats[message.chat_id].messages.append(
                schemas.Message(
                    chat_id=message.chat_id,
                    sender_id=message.sender_id,
                    text=message.text,
                    is_read=message.id not in unread_messages,
                    created_at=message.created_at,
                )
            )
        return list(db_chats.values())
