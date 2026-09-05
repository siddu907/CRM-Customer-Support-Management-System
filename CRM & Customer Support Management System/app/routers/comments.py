from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.repositories.comment import CommentRepository
from app.schemas.comments import CommentCreate, CommentOut, CommentUpdate
from app.services.comment import CommentService
from app.services.ticket import TicketService

router = APIRouter()


@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(ticket_id: int, data: CommentCreate, tasks: BackgroundTasks, current_user: CurrentUser, db: DbSession):
    ticket_service = TicketService(db)
    return CommentService(db).create(current_user, ticket_service.get(ticket_id), data, tasks)


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(ticket_id: int, current_user: CurrentUser, db: DbSession):
    ticket_service = TicketService(db)
    ticket = ticket_service.get(ticket_id)
    ticket_service.can_access(ticket, current_user)
    return CommentRepository(db).for_ticket(ticket_id)


@router.put("/comments/{comment_id}", response_model=CommentOut)
def update_comment(comment_id: int, data: CommentUpdate, current_user: CurrentUser, db: DbSession):
    comment = CommentRepository(db).get(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return CommentService(db).update(current_user, comment, data)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, current_user: CurrentUser, db: DbSession):
    comment = CommentRepository(db).get(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    CommentService(db).delete(current_user, comment)
    return {"message": "Comment deleted successfully"}
