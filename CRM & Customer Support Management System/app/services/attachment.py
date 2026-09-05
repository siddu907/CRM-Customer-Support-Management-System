from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Attachment, User, Ticket
from app.repositories.attachment import AttachmentRepository
from app.schemas.attachments import AttachmentOut
from app.services.audit_log import audit
from app.services.shared import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES, TERMINAL_STATUSES
from app.services.ticket import TicketService
from app.utils.helpers import conflict, forbidden


class AttachmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AttachmentRepository(db)
        self.ticket_service = TicketService(db)

    async def create(self, actor: User, ticket: Ticket, file: UploadFile) -> Attachment:
        self.ticket_service.can_access(ticket, actor, manage=True)
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Closed or cancelled tickets cannot receive attachments")
        original_name = Path(file.filename or "").name
        extension = Path(original_name).suffix.lower()
        if not original_name or extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES[extension]:
            raise HTTPException(status_code=400, detail="The uploaded MIME type does not match the file extension")
        content = await file.read(settings.max_upload_size_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_size_bytes // (1024 * 1024)} MB size limit")
        target_dir = settings.upload_path / str(ticket.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{extension}"
        file_path = target_dir / stored_name
        try:
            file_path.write_bytes(content)
            attachment = self.repo.add(Attachment(ticket_id=ticket.id, uploaded_by=actor.id, file_name=original_name, file_path=str(file_path), file_size=len(content), content_type=file.content_type or "application/octet-stream"))
            audit(self.db, actor.id, "attachment_uploaded", "attachment", attachment.id, new={"ticket_id": ticket.id, "file_name": original_name, "file_size": len(content)})
            self.db.commit()
            return attachment
        except Exception:
            if file_path.exists():
                file_path.unlink()
            self.db.rollback()
            raise

    def delete(self, actor: User, attachment: Attachment) -> None:
        ticket = self.ticket_service.get(attachment.ticket_id)
        self.ticket_service.can_access(ticket, actor, manage=True)
        if actor.role != "admin" and attachment.uploaded_by != actor.id:
            raise forbidden("Only the uploader or an administrator may delete an attachment")
        path = Path(attachment.file_path)
        audit(self.db, actor.id, "attachment_deleted", "attachment", attachment.id, previous={"file_name": attachment.file_name})
        self.db.delete(attachment)
        self.db.commit()
        if path.exists():
            path.unlink()
