from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core import settings

API_KEY_HEADER_SCHEME = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def check_api_key(api_key: Optional[str] = Security(API_KEY_HEADER_SCHEME)):
    if api_key and api_key == settings.API_KEY:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "Authentication Failed",
            "message": "The provided X-API-KEY is missing or invalid.",
            "remedy": "Please include a valid 'X-API-KEY' header in your request.",
        },
    )