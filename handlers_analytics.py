"""Analytics / audit -- value-add health snapshot for the search head."""
from __future__ import annotations

from imperal_sdk import ActionResult

import splunk_client as sc
from app import chat
from handlers_connection import _resolve_connection
from schemas import AuditSearchHeadParams, AuditFinding, AuditReport


@chat.function(
    "audit_search_head",
    "Build one aggregated health report for the connected Splunk instance: saved searches without an alert action, and indexes near their size quota.",
    action_type="read",
    chain_callable=True,
    data_model=AuditReport,
    event="splunk-connector.audit_search_head",
)
async def audit_search_head(ctx, params: AuditSearchHeadParams) -> ActionResult:
    """Build a health report for the connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    findings: list[AuditFinding] = []
    try:
        ss_body = await sc.list_saved_searches(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    ss_entries = ss_body.get("entry", [])
    no_action = 0
    for e in ss_entries:
        c = e.get("content", {})
        if c.get("is_scheduled") and not (c.get("actions", "") or "").strip():
            no_action += 1
            findings.append(AuditFinding(kind="saved_search_no_alert_action", detail=e.get("name", ""), severity="medium"))

    try:
        idx_body = await sc.list_indexes(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    near_quota = 0
    for e in idx_body.get("entry", []):
        c = e.get("content", {})
        cur = int(c.get("currentDBSizeMB", 0) or 0)
        mx = int(c.get("maxTotalDataSizeMB", 0) or 0)
        if mx and cur >= 0.9 * mx:
            near_quota += 1
            findings.append(AuditFinding(kind="index_near_quota", detail=e.get("name", ""), severity="high"))

    return ActionResult.success(data=AuditReport(
        connection_id=conn.get("id", ""),
        saved_searches_total=len(ss_entries),
        saved_searches_without_alert_action=no_action,
        indexes_near_quota=near_quota,
        findings=findings,
    ), summary="Search head audit ready.")
