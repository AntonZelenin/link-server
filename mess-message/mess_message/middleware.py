from fastapi import Request, HTTPException

from mess_message import logger

logger_ = logger.get_logger(__name__, stdout=True)


async def validate_headers(request: Request, call_next: callable):
    if request.headers.get('x-user-id') is None:
        logger_.error('x-user-id header is missing')
        raise HTTPException(status_code=401)
    if request.headers.get('x-username') is None:
        logger_.error('x-username header is missing')
        raise HTTPException(status_code=401)

    return await call_next(request)
