from fastapi import BackgroundTasks

from app.core.database import SessionLocal
from app.models import Notification


def _persist_notifications(user_ids: list[int], ticket_id: int | None, event_type: str, message: str) -> None:
	db = SessionLocal()
	try:
		db.add_all([Notification(user_id=user_id, ticket_id=ticket_id, event_type=event_type, message=message) for user_id in set(user_ids)])
		db.commit()
	finally:
		db.close()


def queue_notifications(tasks: BackgroundTasks, user_ids: list[int], ticket_id: int | None, event_type: str, message: str) -> None:
	if user_ids:
		tasks.add_task(_persist_notifications, user_ids, ticket_id, event_type, message)

