import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    doctor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Register an audit event."""
    entry = AuditLog(
        doctor_id=doctor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        ip_address=ip_address,
        details=json.dumps(details, default=str) if details is not None else None,
    )
    db.add(entry)
