from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models import Comment, Ticket, User
from app.repositories.comment import CommentRepository
from app.schemas.comments import CommentCreate, CommentUpdate
from app.services.audit_log import audit
from app.services.notification import queue_notifications
from app.services.shared import TERMINAL_STATUSES
from app.services.ticket import TicketService
from app.utils.helpers import conflict, forbidden, utcnow


class CommentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CommentRepository(db)
        self.ticket_service = TicketService(db)

    def create(self, actor: User, ticket: Ticket, payload: CommentCreate, tasks: BackgroundTasks) -> Comment:
        self.ticket_service.can_access(ticket, actor, manage=True)
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Closed or cancelled tickets do not accept comments")
        comment = self.repo.add(Comment(ticket_id=ticket.id, user_id=actor.id, content=payload.content.strip()))
        if actor.role == UserRole.SUPPORT_AGENT.value and ticket.first_response_at is None:
            ticket.first_response_at = utcnow()
        audit(self.db, actor.id, "comment_created", "comment", comment.id, new={"ticket_id": ticket.id})
        self.db.commit()
        recipients = [ticket.customer.user_id]
        if ticket.assigned_agent_id:
            recipients.append(ticket.assigned_agent_id)
        queue_notifications(tasks, [user_id for user_id in recipients if user_id != actor.id], ticket.id, "comment_created", f"A new comment was added to ticket {ticket.ticket_number}.")
        return comment

    def update(self, actor: User, comment: Comment, payload: CommentUpdate) -> Comment:
        ticket = self.ticket_service.get(comment.ticket_id)
        self.ticket_service.can_access(ticket, actor, manage=True)
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Closed or cancelled ticket comments cannot be modified")
        if actor.role == UserRole.CUSTOMER.value and comment.user_id != actor.id:
            raise forbidden("Customers cannot modify comments created by support agents")
        if actor.role != UserRole.ADMIN.value and comment.user_id != actor.id:
            raise forbidden("Only the comment author or an administrator may edit a comment")
        before = comment.content
        comment.content = payload.content.strip()
        audit(self.db, actor.id, "comment_updated", "comment", comment.id, previous={"content": before}, new={"content": comment.content})
        self.db.commit()
        return comment

    def delete(self, actor: User, comment: Comment) -> None:
        ticket = self.ticket_service.get(comment.ticket_id)
        self.ticket_service.can_access(ticket, actor, manage=True)
        if actor.role != UserRole.ADMIN.value and comment.user_id != actor.id:
            raise forbidden("Only the comment author or an administrator may delete a comment")
        audit(self.db, actor.id, "comment_deleted", "comment", comment.id, previous={"ticket_id": comment.ticket_id})
        self.db.delete(comment)
        self.db.commit()
