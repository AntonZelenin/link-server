from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from mess_message import schemas, sender, logger, middleware
from mess_message.dependencies import *
from mess_message.managers import ConnectionManager
from mess_message.repository import Repository
from mess_message.schemas import GetChatResults, Chat
from mess_message.settings import get_settings

logger_ = logger.get_logger(__name__, stdout=True)

app = FastAPI()
if not get_settings().debug:
    app.add_middleware(BaseHTTPMiddleware, dispatch=middleware.validate_headers)

conn_manager = ConnectionManager()


@app.websocket('/ws/message/v1/messages')
async def message_socket(websocket: WebSocket, repository: Repository = Depends(get_repository)):
    user_id = websocket.headers.get('x-user-id')
    # todo make conn_manager context manager, and maybe a dependency?
    await conn_manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = schemas.NewMessage.model_validate_json(data)

            if user_id != message.sender_id:
                logger_.error(f'user id in message does not match user id in headers: {user_id}, {message.sender_id}')
                # todo this message will not be shown, it's not http
                # todo logger
                raise HTTPException(status_code=403)
            if not await repository.is_user_in_chat(user_id, message.chat_id):
                logger_.error(f'user {user_id} is not in chat {message.chat_id}')
                # todo this message will not be shown, it's not http
                # todo log that someone tried to send a message to a chat they are not in
                raise HTTPException(status_code=403)

            db_message = await repository.save_message(
                chat_id=message.chat_id,
                sender_id=user_id,
                text=message.text,
            )
            message = schemas.Message(
                chat_id=db_message.chat_id,
                sender_id=db_message.sender_id,
                text=db_message.text,
                is_read=False,
                created_at=db_message.created_at,
            )
            chat_members = await repository.get_chat_members(message.chat_id)
            await sender.send_message(message, chat_members, conn_manager)
    except WebSocketDisconnect as e:
        if e.code != 1001:
            logger_.info(f'websocket disconnected: {user_id}, code {e.code}: {e.reason}')
        await conn_manager.disconnect(user_id, websocket)
    except Exception as e:
        logger_.exception(f'websocket error: {user_id}, {e}')
        await websocket.close(code=1011)
        raise e


@app.get('/api/message/v1/chats/{chat_id}')
async def get_chat(
        chat_id: int,
        x_user_id: str = Header(...),
        repository: Repository = Depends(get_repository),
) -> Chat:
    if not await repository.is_user_in_chat(x_user_id, chat_id):
        raise HTTPException(status_code=403, detail='User is not in chat')

    chat = await repository.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail='Chat not found')

    messages = await repository.get_chat_messages(chat_id)
    unread_messages = await repository.get_unread_message_ids(x_user_id, [chat_id])
    chat_members = await repository.get_chat_members(chat_id)

    return Chat(
        id=chat_id,
        name=chat.name,
        # it doesn't work with chat.chat_members because of greenlet. Why??
        member_ids=[chat_member.user_id for chat_member in chat_members],
        messages=[
            schemas.Message(
                chat_id=message.chat_id,
                sender_id=message.sender_id,
                text=message.text,
                is_read=message.id not in unread_messages,
                created_at=message.created_at,
            )
            for message in messages
        ]
    )


@app.get('/api/message/v1/initial-chats')
async def get_initial_chats(
        chat_provider_: ChatProvider = Depends(get_chat_provider),
        x_user_id: str = Header(...),
) -> GetChatResults:
    return GetChatResults(
        chats=await chat_provider_.get_recent_chats(x_user_id),
    )


@app.get('/api/message/v1/chats')
async def get_chats(
        num_of_chats: int = 20,
        repository: Repository = Depends(get_repository),
        x_user_id: str = Header(...),
) -> GetChatResults:
    # Assuming Redis always has the latest data (possibly with a small delay)
    # 1. Use an ordered set in Redis to store ordered chats based on the last message timestamp
    # 2. Keep the recent messages in the cache. Write/trim complexity will be O(1) for every new message, so I think even for high message rate it should be fine
    # 3. Get recent chat ids from the cache and fallback to the db if not found
    # 4. Get recent messages from the cache and fallback to the db if not found
    # 5. Cache everything that is not in the cache
    # 6. Use separate endpoints for initial chats retrieval and for getting more chats when scrolling
    # todo wtf is this? I probably should use provider
    res = list(await repository.get_recent_user_chats(x_user_id, [], num_of_chats))

    chats: dict[int, Chat] = {}
    for row in res:
        if row["id"] not in chats:
            chats[row["id"]] = Chat(id=row["id"], name=row["name"], member_ids=[], messages=[])

        chats[row["id"]].member_ids.append(row["user_id"])

    messages = await repository.get_chats_messages([chat.id for chat in chats.values()])
    unread_messages = await repository.get_unread_message_ids(x_user_id, [chat.id for chat in chats.values()])

    for message in messages:
        chats[message.chat_id].messages.append(
            schemas.Message(
                chat_id=message.chat_id,
                sender_id=message.sender_id,
                text=message.text,
                is_read=message.id not in unread_messages,
                created_at=message.created_at,
            )
        )

    return GetChatResults(chats=list(chats.values()))


@app.post('/api/message/v1/chats')
async def create_chat(
        new_chat: schemas.NewChat,
        x_user_id: str = Header(...),
        repository: Repository = Depends(get_repository),
) -> Chat:
    chat_db = await repository.create_chat(new_chat.name)

    try:
        await repository.add_chat_members(chat_db.id, list(new_chat.member_ids))
        await repository.save_message(chat_db.id, x_user_id, new_chat.first_message)
    except Exception as e:
        logger_.exception(f'error creating chat: {e}')
        await repository.delete_chat(chat_db.id)
        raise e

    db_messages = await repository.get_chats_messages([chat_db.id])
    chat_members = await repository.get_chat_members(chat_db.id)

    first_message = schemas.Message(
        chat_id=db_messages[0].chat_id,
        sender_id=db_messages[0].sender_id,
        text=db_messages[0].text,
        is_read=False,
        created_at=db_messages[0].created_at,
    )
    # todo why I cannot use chat_db.chat_members here? it argues on greenlet.. something related to async
    await sender.send_message(first_message, chat_members, conn_manager)

    return Chat(
        id=chat_db.id,
        name=chat_db.name,
        member_ids=new_chat.member_ids,
        messages=[
            schemas.Message(
                chat_id=message.chat_id,
                sender_id=message.sender_id,
                text=message.text,
                is_read=True,
                created_at=message.created_at,
            )
            for message in db_messages
        ]
    )


@app.post('/api/message/v1/chats/{chat_id}/read')
async def mark_chat_as_read(
        chat_id: int,
        x_user_id: str = Header(...),
        repository: Repository = Depends(get_repository),
):
    if not await repository.is_user_in_chat(x_user_id, chat_id):
        raise HTTPException(status_code=403, detail='User is not in chat')

    await repository.read_all_messages(chat_id, x_user_id)
    return {"message": "ok"}
