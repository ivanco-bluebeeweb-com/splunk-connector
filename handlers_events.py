"""HTTP Event Collector -- send events into Splunk from Imperal."""
from __future__ import annotations

from imperal_sdk import ActionResult

import splunk_client as sc
from app import chat
from handlers_connection import _load_hec_tokens, _resolve_connection
from schemas import SendEventParams, SendEventResult


@chat.function(
    "send_event",
    "Send an event into Splunk via HTTP Event Collector (HEC). Requires a saved HEC token (save_hec_token).",
    action_type="write",
    chain_callable=True,
    data_model=SendEventResult,
    event="splunk-connector.send_event",
    effects=["create:resource"],
)
async def send_event(ctx, params: SendEventParams) -> ActionResult:
    """Send an event into Splunk via HTTP Event Collector."""
    tokens = await _load_hec_tokens(ctx)
    token_entry = next((t for t in tokens if t.get("id") == params.token_id), None)
    if not token_entry:
        return ActionResult.error(f"No HEC token found with id '{params.token_id}'.")
    conn = await _resolve_connection(ctx, token_entry.get("connection_id", ""))
    if isinstance(conn, ActionResult):
        return conn
    hec_base = conn.get("base_url", "").rstrip("/")
    # HEC listens on 8088 by default, management API on 8089 -- if the
    # connection's base_url still points at the management port, swap it.
    if ":8089" in hec_base:
        hec_base = hec_base.replace(":8089", ":8088")
    try:
        await sc.send_hec_event(ctx, hec_base, token_entry.get("hec_token", ""), params.event, params.source, params.sourcetype, params.index)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=SendEventResult(ok=True), summary="Event sent to Splunk via HEC.")
