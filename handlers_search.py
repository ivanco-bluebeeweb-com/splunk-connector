"""Search jobs -- dispatch, poll status, get paginated results. Splunk's
search API is asynchronous job-based (see splunk_client.py's dispatch_search/
get_search_status/get_search_results), not a synchronous request-response.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import splunk_client as sc
from app import chat
from handlers_connection import _resolve_connection
from schemas import (
    DispatchSearchParams, SearchJob,
    GetSearchStatusParams, GetSearchResultsParams, SearchResultRow, SearchResultList,
    DeleteResult,
)


def _job_from_status(sid: str, body: dict) -> SearchJob:
    entry = (body.get("entry") or [{}])[0]
    content = entry.get("content", {})
    return SearchJob(
        sid=sid,
        status=content.get("dispatchState", ""),
        dispatch_state=content.get("dispatchState", ""),
        scan_count=int(content.get("scanCount", 0) or 0),
        event_count=int(content.get("eventCount", 0) or 0),
        result_count=int(content.get("resultCount", 0) or 0),
        run_duration=float(content.get("runDuration", 0.0) or 0.0),
        is_done=content.get("isDone", False) in (True, "1", 1),
    )


@chat.function(
    "dispatch_search",
    "Start a new Splunk search job (SPL query). Returns a search job id (sid) -- poll get_search_status, then get_search_results once done.",
    action_type="write",
    chain_callable=True,
    data_model=SearchJob,
    event="splunk-connector.dispatch_search",
    effects=["create:resource"],
)
async def dispatch_search(ctx, params: DispatchSearchParams) -> ActionResult:
    """Start a new Splunk search job."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.dispatch_search(ctx, conn, params.spl_query, params.earliest_time, params.latest_time)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    sid = body.get("sid", "")
    if not sid:
        return ActionResult.error("Splunk did not return a search job id.")
    return ActionResult.success(data=SearchJob(sid=sid, status="queued", is_done=False), summary=f"Search job {sid} started.")


@chat.function(
    "get_search_status",
    "Read a search job's current status -- whether it's done, and scan/event/result counts so far.",
    action_type="read",
    chain_callable=True,
    data_model=SearchJob,
    event="splunk-connector.get_search_status",
)
async def get_search_status(ctx, params: GetSearchStatusParams) -> ActionResult:
    """Read a search job's current status."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.get_search_status(ctx, conn, params.sid)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=_job_from_status(params.sid, body))


@chat.function(
    "get_search_results",
    "Read a page of results from a completed (or still-running) search job.",
    action_type="read",
    chain_callable=True,
    data_model=SearchResultList,
    event="splunk-connector.get_search_results",
)
async def get_search_results(ctx, params: GetSearchResultsParams) -> ActionResult:
    """Read a page of results from a search job."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.get_search_results(ctx, conn, params.sid, params.offset, params.count)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    rows = []
    for row in body.get("results", []):
        fields = {k: v for k, v in row.items() if not k.startswith("_")}
        rows.append(SearchResultRow(fields_json=str(fields), raw=str(row.get("_raw", ""))[:2000]))
    return ActionResult.success(data=SearchResultList(items=rows))


@chat.function(
    "cancel_search",
    "Cancel a running search job.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="splunk-connector.cancel_search",
    effects=["update:resource"],
)
async def cancel_search(ctx, params: GetSearchStatusParams) -> ActionResult:
    """Cancel a running search job."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await sc.cancel_search(ctx, conn, params.sid)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True), summary=f"Search job {params.sid} cancelled.")
