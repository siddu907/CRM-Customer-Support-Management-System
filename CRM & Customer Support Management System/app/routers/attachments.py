from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.core.dependencies import CurrentUser, DbSession
from app.repositories.attachment import AttachmentRepository
from app.schemas.attachments import AttachmentOut
from app.services.attachment import AttachmentService
from app.services.ticket import TicketService

router = APIRouter()


@router.post("/tickets/{ticket_id}/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(ticket_id: int, file: UploadFile = File(...), current_user: CurrentUser = None, db: DbSession = None):
    ticket = TicketService(db).get(ticket_id)
    return await AttachmentService(db).create(current_user, ticket, file)


@router.get("/tickets/{ticket_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(ticket_id: int, current_user: CurrentUser, db: DbSession):
    ticket_service = TicketService(db)
    ticket = ticket_service.get(ticket_id)
    ticket_service.can_access(ticket, current_user)
    return AttachmentRepository(db).for_ticket(ticket_id)


@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id: int, current_user: CurrentUser, db: DbSession):
    attachment = AttachmentRepository(db).get(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    ticket_service = TicketService(db)
    ticket_service.can_access(ticket_service.get(attachment.ticket_id), current_user)
    path = Path(attachment.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file is unavailable")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.file_name)


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, current_user: CurrentUser, db: DbSession):
    attachment = AttachmentRepository(db).get(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    AttachmentService(db).delete(current_user, attachment)
    return {"message": "Attachment deleted successfully"}
