from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.schemas.orders import (
    FileResponse,
    UploadConfirm,
    UploadRequest,
    UploadURLResponse,
)
from app.services import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/request-upload", response_model=UploadURLResponse)
async def request_upload(
    data: UploadRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await file_service.generate_upload_url(
        user_id,
        data.filename,
        data.file_type,
        data.mime_type,
        data.size_bytes,
        db,
        data.order_id,
    )


@router.post("/confirm", response_model=FileResponse)
async def confirm_upload(
    data: UploadConfirm,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await file_service.confirm_upload(
        db,
        data.order_id,
        data.key,
        data.filename,
        data.url,
        data.file_type,
        data.mime_type,
        data.size_bytes,
        user_id,
    )


@router.get("/{order_id}", response_model=list[FileResponse])
async def list_files(
    order_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await file_service.get_order_files(db, order_id, user_id)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await file_service.delete_file(db, file_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
