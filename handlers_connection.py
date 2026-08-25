"""Connection management: connect/disconnect Splunk instances, save/list/
delete HEC tokens. Same shape as PagerDuty Connector's handlers_connection.py
-- async, one secret holding a JSON array per store, ActionResult.success()/.error().
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import splunk_client as sc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectSplunkParams, ProviderConnection, ProviderConnectionList,
    DisconnectSplunkParams, DeleteResult,
    SaveHecTokenParams, HecTokenEntry, HecTokenList, DeleteHecTokenParams,
)

_CONN_SECRET = "splunk_connections"
_HEC_SECRET = "splunk_hec_tokens"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONN_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_CONN_SECRET, json.dumps(items))


async def _load_hec_tokens(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_HEC_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_hec_tokens(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_HEC_SECRET, json.dumps(items))


async def _resolve_connection(ctx, connection_id: str):
    conns = await _load_connections(ctx)
    if not conns:
        return ActionResult.error("No Splunk instance connected yet.")
    if connection_id:
        for c in conns:
            if c.get("id") == connection_id:
                return c
        return ActionResult.error(f"No connection found with id '{connection_id}'.")
    if len(conns) == 1:
        return conns[0]
    return ActionResult.error("Multiple Splunk connections exist -- pass connection_id explicitly.")


@chat.function(
    "connect_splunk",
    "Connect your own self-hosted or Splunk Cloud instance by saving its base URL "
    "plus an auth token or username/password, after checking it actually works. "
    "Get a token from Splunk: Settings > Tokens > New Token.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="splunk-connector.connect_splunk",
    effects=["splunk.provider.connected"],
)
async def connect_splunk(ctx, params: ConnectSplunkParams) -> ActionResult:
    """Connect your own self-hosted or Splunk Cloud instance."""
    base_url = params.base_url.strip().rstrip("/")
    if not base_url:
        return ActionResult.error("base_url is required, e.g. https://splunk.mycompany.com:8089")

    conn = {"base_url": base_url}
    if params.auth_mode == "password":
        if not params.username or not params.password:
            return ActionResult.error("username and password are required for auth_mode='password'.")
        try:
            session_key = await sc.get_session_key(ctx, base_url, params.username, params.password)
        except sc.ClientFail as exc:
            return ActionResult.error(str(exc))
        conn["session_key"] = session_key
        conn["username"] = params.username
    else:
        if not params.auth_token:
            return ActionResult.error("auth_token is required for auth_mode='token'.")
        conn["auth_token"] = params.auth_token

    try:
        await sc.validate_connection(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(f"Could not validate Splunk connection: {exc}")

    conns = await _load_connections(ctx)
    conn["id"] = str(uuid.uuid4())
    conn["label"] = params.label or base_url
    conns.append(conn)
    await _save_connections(ctx, conns)

    return ActionResult.success(
        data=ProviderConnection(id=conn["id"], title=conn["label"], connected=True, base_url=base_url),
        summary=f"Connected to Splunk at {base_url}.",
        refresh_panels=["splunk_main", "splunk_settings"],
    )


@chat.function(
    "list_connections",
    "List the connected Splunk instances.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
    event="splunk-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Splunk instances."""
    conns = await _load_connections(ctx)
    items = [
        ProviderConnection(id=c.get("id", ""), title=c.get("label", c.get("base_url", "")),
                            connected=True, base_url=c.get("base_url", ""))
        for c in conns
    ]
    return ActionResult.success(data=ProviderConnectionList(items=items), summary=f"{len(items)} instance(s) connected.")


@chat.function(
    "disconnect_splunk",
    "Disconnect a Splunk instance: deletes the saved credentials. Nothing in Splunk itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="splunk-connector.disconnect_splunk",
    effects=["splunk.provider.disconnected"],
)
async def disconnect_splunk(ctx, params: DisconnectSplunkParams) -> ActionResult:
    """Disconnect a Splunk instance: deletes the saved credentials."""
    conns = await _load_connections(ctx)
    remaining = [c for c in conns if c.get("id") != params.connection_id]
    if len(remaining) == len(conns):
        return ActionResult.error(f"No connection found with id '{params.connection_id}'.")
    await _save_connections(ctx, remaining)
    hec = await _load_hec_tokens(ctx)
    hec = [h for h in hec if h.get("connection_id") != params.connection_id]
    await _save_hec_tokens(ctx, hec)
    return ActionResult.success(
        data=DeleteResult(ok=True, detail="Disconnected."),
        summary="Splunk instance disconnected.",
        refresh_panels=["splunk_main", "splunk_settings"],
    )


@chat.function(
    "save_hec_token",
    "Save an HTTP Event Collector token for a connected Splunk instance, so send_event can push events into it. "
    "Get one from Settings > Data Inputs > HTTP Event Collector > New Token.",
    action_type="write",
    chain_callable=True,
    data_model=HecTokenEntry,
    event="splunk-connector.save_hec_token",
    effects=["splunk.hec_token.saved"],
)
async def save_hec_token(ctx, params: SaveHecTokenParams) -> ActionResult:
    """Save an HTTP Event Collector token for a connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    tokens = await _load_hec_tokens(ctx)
    entry = {
        "id": str(uuid.uuid4()),
        "connection_id": params.connection_id,
        "hec_token": params.hec_token,
        "label": params.label or "HEC token",
    }
    tokens.append(entry)
    await _save_hec_tokens(ctx, tokens)
    return ActionResult.success(
        data=HecTokenEntry(id=entry["id"], connection_id=params.connection_id, label=entry["label"]),
        summary="HEC token saved.",
        refresh_panels=["splunk_settings"],
    )


@chat.function(
    "list_hec_tokens",
    "List saved HTTP Event Collector tokens (never reveals the secret value).",
    action_type="read",
    chain_callable=True,
    data_model=HecTokenList,
    event="splunk-connector.list_hec_tokens",
)
async def list_hec_tokens(ctx, params: NoParams) -> ActionResult:
    """List saved HTTP Event Collector tokens."""
    tokens = await _load_hec_tokens(ctx)
    items = [HecTokenEntry(id=t.get("id", ""), connection_id=t.get("connection_id", ""), label=t.get("label", "")) for t in tokens]
    return ActionResult.success(data=HecTokenList(items=items), summary=f"{len(items)} HEC token(s) saved.")


@chat.function(
    "delete_hec_token",
    "Permanently delete a saved HEC token. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="splunk-connector.delete_hec_token",
    effects=["splunk.hec_token.deleted"],
)
async def delete_hec_token(ctx, params: DeleteHecTokenParams) -> ActionResult:
    """Permanently delete a saved HEC token."""
    tokens = await _load_hec_tokens(ctx)
    remaining = [t for t in tokens if t.get("id") != params.token_id]
    if len(remaining) == len(tokens):
        return ActionResult.error(f"No HEC token found with id '{params.token_id}'.")
    await _save_hec_tokens(ctx, remaining)
    return ActionResult.success(data=DeleteResult(ok=True), summary="HEC token deleted.", refresh_panels=["splunk_settings"])
