from fastapi import APIRouter
from app.verticals import list_verticals

router = APIRouter()


@router.get("/verticals")
async def get_verticals():
    return list_verticals()
