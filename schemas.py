"""Pydantic params models + SDL entity contracts for Splunk Connector.

All params models are module-scope (V17 federal invariant). Organized by
domain to match handlers_*.py split (connection, search, saved searches,
indexes, users/roles, HEC events, analytics/audit).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ── Connection ──────────────────────────────────────────────────────────

class ConnectSplunkParams(BaseModel):
    base_url: str = Field(
        "", description="Your Splunk management API base URL, e.g. https://splunk.mycompany.com:8089",
    )
    auth_mode: str = Field(
        "token", description="Auth mode: 'token' (Splunk auth token) or 'password' (username+password).",
    )
    auth_token: str = Field("", description="Splunk auth token (Settings > Tokens > New Token).")
    username: str = Field("", description="Splunk username, if auth_mode='password'.")
    password: str = Field("", description="Splunk password, if auth_mode='password'.")
    label: str = Field("", description="Optional friendly name for this connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    base_url: str = ""


class ProviderConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ProviderConnection] = []


class DisconnectSplunkParams(BaseModel):
    connection_id: str = Field(..., description="Connection id from list_connections.")


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = True
    detail: str = ""


class SaveHecTokenParams(BaseModel):
    connection_id: str = Field(..., description="Connection id this HEC token belongs to.")
    hec_token: str = Field(..., description="HTTP Event Collector token (Settings > Data Inputs > HTTP Event Collector).")
    label: str = Field("", description="Optional friendly name, e.g. the target index.")


class HecTokenEntry(sdl.Entity):
    title: str = ""
    id: str = ""
    connection_id: str = ""
    label: str = ""


class HecTokenList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[HecTokenEntry] = []


class DeleteHecTokenParams(BaseModel):
    token_id: str = Field(..., description="HEC token id from list_hec_tokens.")


# ── Search ──────────────────────────────────────────────────────────────

class DispatchSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    spl_query: str = Field(..., description="Splunk SPL query, e.g. 'search index=security sourcetype=auth | stats count by user'")
    earliest_time: str = Field("-24h", description="Search time window start, e.g. -24h, -7d.")
    latest_time: str = Field("now", description="Search time window end.")


class SearchJob(sdl.Entity):
    id: str = ""
    title: str = ""
    sid: str = ""
    status: str = ""
    dispatch_state: str = ""
    scan_count: int = 0
    event_count: int = 0
    result_count: int = 0
    run_duration: float = 0.0
    is_done: bool = False


class SearchDispatchResult(sdl.Entity):
    id: str = ""
    title: str = ""
    sid: str = ""


class GetSearchStatusParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    sid: str = Field(..., description="Search job id (sid) from dispatch_search.")


class GetSearchResultsParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    sid: str = Field(..., description="Search job id (sid) from dispatch_search.")
    offset: int = Field(0, description="Pagination offset into results.")
    count: int = Field(100, description="Max results to return (1-1000).")


class SearchResultRow(sdl.Entity):
    id: str = ""
    title: str = ""
    fields_json: str = ""  # JSON-encoded dict of field->value, since fields vary per search
    raw: str = ""


class SearchResultList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SearchResultRow] = []


class CancelSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    sid: str = Field(..., description="Search job id (sid) to cancel.")


# ── Saved searches ──────────────────────────────────────────────────────

class ListSavedSearchesParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")


class SavedSearch(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    search: str = ""
    cron_schedule: str = ""
    is_scheduled: bool = False
    has_alert_action: bool = False
    next_scheduled_time: str = ""


class SavedSearchList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SavedSearch] = []


class GetSavedSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    name: str = Field(..., description="Saved search name.")


class CreateSavedSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    name: str = Field(..., description="New saved search name.")
    search: str = Field(..., description="SPL query for this saved search.")
    cron_schedule: str = Field("", description="Cron schedule, e.g. '*/15 * * * *'; empty = not scheduled.")
    is_scheduled: bool = Field(False, description="Whether this saved search runs on a schedule.")


class UpdateSavedSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    name: str = Field(..., description="Saved search name to update.")
    search: str = Field("", description="New SPL query; empty = unchanged.")
    cron_schedule: str = Field("", description="New cron schedule; empty = unchanged.")


class DeleteSavedSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    name: str = Field(..., description="Saved search name to delete.")


class DispatchSavedSearchParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")
    name: str = Field(..., description="Saved search name to run now.")


# ── Indexes ─────────────────────────────────────────────────────────────

class ListIndexesParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")


class SplunkIndex(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    current_db_size_mb: float = 0.0
    max_total_data_size_mb: float = 0.0
    total_event_count: int = 0
    disabled: bool = False
    near_quota: bool = False


class IndexList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SplunkIndex] = []


# ── Users / roles ───────────────────────────────────────────────────────

class ListUsersParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")


class SplunkUser(sdl.Entity):
    id: str = ""
    title: str = ""
    username: str = ""
    real_name: str = ""
    roles: str = ""  # comma-joined
    email: str = ""


class UserList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SplunkUser] = []


class ListRolesParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")


class SplunkRole(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    capabilities: str = ""  # comma-joined, truncated


class RoleList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[SplunkRole] = []


# ── HEC events ──────────────────────────────────────────────────────────

class SendEventParams(BaseModel):
    token_id: str = Field(..., description="HEC token id from list_hec_tokens.")
    event: str = Field(..., description="Event payload text or JSON to ingest.")
    source: str = Field("imperal", description="Source field for the event.")
    sourcetype: str = Field("imperal:event", description="Sourcetype field for the event.")
    index: str = Field("", description="Target index; empty = HEC token's default index.")


class SendEventResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = True
    detail: str = ""


# ── Analytics / audit ───────────────────────────────────────────────────

class AuditSearchHeadParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the only connected instance.")


class AuditFinding(sdl.Entity):
    id: str = ""
    title: str = ""
    kind: str = ""
    detail: str = ""
    severity: str = ""


class AuditReport(sdl.Entity):
    id: str = ""
    title: str = ""
    connection_id: str = ""
    saved_searches_total: int = 0
    saved_searches_without_alert_action: int = 0
    indexes_near_quota: int = 0
    findings: list[AuditFinding] = []
