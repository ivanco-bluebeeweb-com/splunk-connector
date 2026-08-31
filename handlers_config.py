"""Saved searches (alerts) and indexes -- configuration CRUD + dispatch.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import splunk_client as sc
from app import chat
from handlers_connection import _resolve_connection
from schemas import (
    ListSavedSearchesParams, SavedSearch, SavedSearchList,
    CreateSavedSearchParams, UpdateSavedSearchParams, DeleteSavedSearchParams,
    DispatchSavedSearchParams, DeleteResult, SearchDispatchResult,
    ListIndexesParams, SplunkIndex, IndexList,
    ListUsersParams, SplunkUser, UserList,
    ListRolesParams, SplunkRole, RoleList,
)


def _saved_search_from_entry(entry: dict) -> SavedSearch:
    content = entry.get("content", {})
    actions = content.get("actions", "") or ""
    return SavedSearch(
        name=entry.get("name", ""),
        search=content.get("search", ""),
        cron_schedule=content.get("cron_schedule", ""),
        is_scheduled=bool(content.get("is_scheduled", False)),
        has_alert_action=bool(actions.strip()),
        disabled=bool(content.get("disabled", False)),
    )


@chat.function(
    "list_saved_searches",
    "List saved searches (and alerts) configured on the connected Splunk instance.",
    action_type="read",
    chain_callable=True,
    data_model=SavedSearchList,
    event="splunk-connector.list_saved_searches",
)
async def list_saved_searches(ctx, params: ListSavedSearchesParams) -> ActionResult:
    """List saved searches configured on the connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.list_saved_searches(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = [_saved_search_from_entry(e) for e in body.get("entry", [])]
    return ActionResult.success(data=SavedSearchList(items=items), summary="Saved searches listed.")


@chat.function(
    "create_saved_search",
    "Create a new saved search, optionally with a cron schedule to run it as an alert.",
    action_type="write",
    chain_callable=True,
    data_model=SavedSearch,
    event="splunk-connector.create_saved_search",
    effects=["create:resource"],
)
async def create_saved_search(ctx, params: CreateSavedSearchParams) -> ActionResult:
    """Create a new saved search."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await sc.create_saved_search(ctx, conn, params.name, params.search, params.cron_schedule)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(
        data=SavedSearch(name=params.name, search=params.search, cron_schedule=params.cron_schedule, is_scheduled=bool(params.cron_schedule)),
        summary=f"Saved search '{params.name}' created.", refresh_panels=["splunk_main"])


@chat.function(
    "update_saved_search",
    "Update selected fields of an existing saved search. Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=SavedSearch,
    event="splunk-connector.update_saved_search",
    effects=["update:resource"],
)
async def update_saved_search(ctx, params: UpdateSavedSearchParams) -> ActionResult:
    """Update an existing saved search."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await sc.update_saved_search(ctx, conn, params.name, params.search or None, params.cron_schedule or None)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(
        data=SavedSearch(name=params.name, search=params.search or "", cron_schedule=params.cron_schedule or ""),
        summary=f"Saved search '{params.name}' updated.", refresh_panels=["splunk_main"])


@chat.function(
    "delete_saved_search",
    "Permanently delete a saved search. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="splunk-connector.delete_saved_search",
    effects=["delete:resource"],
)
async def delete_saved_search(ctx, params: DeleteSavedSearchParams) -> ActionResult:
    """Permanently delete a saved search."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        await sc.delete_saved_search(ctx, conn, params.name)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    return ActionResult.success(data=DeleteResult(ok=True), summary=f"Saved search '{params.name}' deleted.", refresh_panels=["splunk_main"])


@chat.function(
    "dispatch_saved_search",
    "Run a saved search right now, on demand, regardless of its schedule.",
    action_type="write",
    chain_callable=True,
    data_model=SearchDispatchResult,
    event="splunk-connector.dispatch_saved_search",
    effects=["create:resource"],
)
async def dispatch_saved_search(ctx, params: DispatchSavedSearchParams) -> ActionResult:
    """Run a saved search on demand."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.dispatch_saved_search(ctx, conn, params.name)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    sid = body.get("sid", "")
    return ActionResult.success(data=SearchDispatchResult(sid=sid), summary=f"Saved search '{params.name}' dispatched (sid={sid}).")


@chat.function(
    "list_indexes",
    "List indexes configured on the connected Splunk instance, with current/max size.",
    action_type="read",
    chain_callable=True,
    data_model=IndexList,
    event="splunk-connector.list_indexes",
)
async def list_indexes(ctx, params: ListIndexesParams) -> ActionResult:
    """List indexes configured on the connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.list_indexes(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = []
    for e in body.get("entry", []):
        c = e.get("content", {})
        cur = int(c.get("currentDBSizeMB", 0) or 0)
        mx = int(c.get("maxTotalDataSizeMB", 0) or 0)
        items.append(SplunkIndex(
            name=e.get("name", ""), current_size_mb=cur, max_size_mb=mx,
            disabled=bool(c.get("disabled", False)),
            near_quota=bool(mx and cur >= 0.9 * mx),
        ))
    return ActionResult.success(data=IndexList(items=items), summary="Indexes listed.")


@chat.function(
    "list_users",
    "List users registered on the connected Splunk instance.",
    action_type="read",
    chain_callable=True,
    data_model=UserList,
    event="splunk-connector.list_users",
)
async def list_users(ctx, params: ListUsersParams) -> ActionResult:
    """List users registered on the connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.list_users(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = []
    for e in body.get("entry", []):
        c = e.get("content", {})
        items.append(SplunkUser(
            username=e.get("name", ""), real_name=c.get("realname", ""),
            roles=",".join(c.get("roles", []) or []), email=c.get("email", ""),
        ))
    return ActionResult.success(data=UserList(items=items), summary="Users listed.")


@chat.function(
    "list_roles",
    "List roles configured on the connected Splunk instance, with their capabilities.",
    action_type="read",
    chain_callable=True,
    data_model=RoleList,
    event="splunk-connector.list_roles",
)
async def list_roles(ctx, params: ListRolesParams) -> ActionResult:
    """List roles configured on the connected Splunk instance."""
    conn = await _resolve_connection(ctx, params.connection_id)
    if isinstance(conn, ActionResult):
        return conn
    try:
        body = await sc.list_roles(ctx, conn)
    except sc.ClientFail as exc:
        return ActionResult.error(str(exc))
    items = []
    for e in body.get("entry", []):
        c = e.get("content", {})
        caps = c.get("capabilities", []) or []
        items.append(SplunkRole(name=e.get("name", ""), capabilities=",".join(caps[:20])))
    return ActionResult.success(data=RoleList(items=items), summary="Roles listed.")
