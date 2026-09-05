from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(db: Session, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, *, previous: dict | None = None, new: dict | None = None, description: str | None = None) -> AuditLog:
	if description is None:
		description = f"{action.replace('_', ' ').capitalize()} for {entity_type} {entity_id}."
	record = AuditLog(user_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, previous_value=previous, new_value=new, description=description)
	db.add(record)
	return record

