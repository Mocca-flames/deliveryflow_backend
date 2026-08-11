from fastapi import APIRouter

router = APIRouter()


@router.post("/upload")
async def upload_document():
    return {"message": "upload document"}


@router.get("/{doc_id}/download")
async def download_document(doc_id: str):
    return {"doc_id": doc_id, "action": "download"}
