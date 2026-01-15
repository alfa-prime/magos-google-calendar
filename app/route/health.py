from fastapi import APIRouter, Depends

from app.core import check_api_key

router = APIRouter(prefix="/health", tags=["Health check"], dependencies=[Depends(check_api_key)])


@router.get("/ping")
def health_check():
    return {"pong!"}