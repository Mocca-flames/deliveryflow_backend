from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    # Placeholder — implement JWT auth
    return {"message": "login endpoint"}


@router.post("/refresh")
async def refresh():
    # Placeholder — implement token refresh
    return {"message": "refresh endpoint"}
