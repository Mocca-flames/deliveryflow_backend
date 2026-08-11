from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_trips():
    return {"message": "list trips"}


@router.post("/")
async def create_trip():
    return {"message": "create trip"}


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    return {"trip_id": trip_id}


@router.post("/{trip_id}/award-contract")
async def award_contract(trip_id: str):
    return {"trip_id": trip_id, "action": "award-contract"}
