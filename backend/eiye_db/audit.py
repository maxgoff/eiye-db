"""Audit trail: every query and discovery is recorded."""

from datetime import datetime, timezone
from typing import Any

from eiye_db import db


def record(
    action: str,
    resource_type: str,
    resource_id: str,
    api_key_id: str | None = None,
    datasource_id: str | None = None,
    details: dict[str, Any] | None = None,
    success: bool = True,
) -> None:
    with db.session() as s:
        s.add(
            db.AuditRow(
                timestamp=datetime.now(timezone.utc),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                api_key_id=api_key_id,
                datasource_id=datasource_id,
                details=details or {},
                success=success,
            )
        )
        s.commit()


def recent(limit: int = 100) -> list[dict[str, Any]]:
    with db.session() as s:
        rows = s.query(db.AuditRow).order_by(db.AuditRow.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "api_key_id": r.api_key_id,
                "datasource_id": r.datasource_id,
                "details": r.details,
                "success": r.success,
            }
            for r in rows
        ]
