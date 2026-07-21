"""Market-test metrics, derived from the audit trail.

The audit log already records every create/test/discover/query with a
timestamp, success flag, and (for queries) PII-redaction counts, so the
metrics that matter for the wedge market test are aggregated from it rather
than kept in separate counters:

- time-to-first-datasource : first_datasource_at (a harness compares this to
  when the user started)
- adoption / usage         : datasources, actions, queries.total
- reliability              : queries.success_rate
- governance is working    : pii_redactions.total and by_type
"""

from collections import Counter

from eiye_db import db, registry


def collect() -> dict:
    with db.session() as s:
        rows = s.query(db.AuditRow).order_by(db.AuditRow.timestamp).all()
        # Pull fields out inside the session; rows are detached afterward.
        events = [(r.action, r.resource_type, r.success, r.timestamp, r.details or {}) for r in rows]

    action_counts: Counter = Counter(a for a, *_ in events)
    queries = [e for e in events if e[0] == "query"]
    succeeded = sum(1 for e in queries if e[2])

    pii_by_type: Counter = Counter()
    for *_, details in queries:
        for kind, n in details.get("pii_counts", {}).items():
            pii_by_type[kind] += n

    def first_at(pred) -> str | None:
        for action, resource_type, success, ts, _ in events:  # events are timestamp-ascending
            if pred(action, resource_type, success):
                return ts.isoformat()
        return None

    return {
        "datasources": len(registry.list_all()),
        "actions": dict(action_counts),
        "queries": {
            "total": len(queries),
            "succeeded": succeeded,
            "failed": len(queries) - succeeded,
            "success_rate": round(succeeded / len(queries), 3) if queries else None,
        },
        "pii_redactions": {"total": sum(pii_by_type.values()), "by_type": dict(pii_by_type)},
        "first_datasource_at": first_at(lambda a, rt, _: a == "create" and rt == "datasource"),
        "first_successful_query_at": first_at(lambda a, _rt, ok: a == "query" and ok),
        "last_activity_at": events[-1][3].isoformat() if events else None,
    }
