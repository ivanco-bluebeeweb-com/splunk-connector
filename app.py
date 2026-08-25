"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK, SAME REASONING AS PagerDuty Connector / MuleSoft Connector.

Splunk is the user's OWN self-hosted or Splunk Cloud instance -- Imperal
cannot broker access to someone else's log/search infrastructure
centrally. The user provides their own base_url plus an auth token (or
username/password), Vault-encrypted via `ctx.secrets`, and every call
runs against their own Splunk instance.

WHY BASE_URL IS MANDATORY AND SSRF-VALIDATED.

Splunk has no single multi-tenant hosted endpoint the way Stripe/HubSpot
do -- every customer runs their own management API on their own host
(default port 8089), self-hosted or on Splunk Cloud with a per-tenant
hostname. `connect_splunk` normalizes and validates base_url through the
platform's SSRF guard before ever calling it, per `APP_SAFETY_CHECKLIST.md`.

WHY TWO AUTH MODES (auth_token OR username+password) INSTEAD OF ONE.

Splunk's REST API accepts a long-lived auth token (Settings > Tokens,
confirmed CONNECTOR_DISCOVERY.md 2026-08-24) OR classic Basic auth via
username/password, which Splunk exchanges for a short-lived session key.
Token is preferred (no expiry dance) but not every instance has token
auth enabled, so both are supported, same "api_key vs username/password"
precedent elsewhere in the portfolio.

WHY THE HEC TOKEN IS A SEPARATE, PER-CONNECTION SECRET, NOT PART OF THE
MAIN CONNECT FORM.

HTTP Event Collector (port 8088) is a completely different auth surface
-- a token scoped to event ingestion only, unrelated to the management
API credential. A user may not want or have HEC enabled at all, so it is
added later from the settings screen, same "add secondary secret after
connect" precedent as PagerDuty Connector's Integration Keys.

CONNECTIONS ARE STORED AS ONE JSON ARRAY, SAME AS PagerDuty Connector.

`splunk_connections` holds a JSON array of
`{id, label, base_url, auth_token, session_key, username}` objects, and
every tool's `connection_id` parameter addresses one entry -- see
handlers_connection.py's `_load_connections`/`_save_connections`.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "splunk-connector",
    version="0.1.0",
    display_name="Splunk",
    description=(
        "Connect your own Splunk instance (self-hosted or Splunk Cloud) to "
        "run searches, manage saved searches/alerts, indexes, users and "
        "roles, send events via HTTP Event Collector, and audit search-head "
        "health -- from Imperal. Uses your own auth token (or username/"
        "password) -- nothing is hosted or proxied by Imperal beyond the "
        "request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "splunk:read",
        "splunk:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="splunk",
    description=(
        "Splunk Connector -- connect your own Splunk instance via base URL "
        "plus auth token (or username/password), then run SPL searches, "
        "manage saved searches/alerts, indexes, users, roles, send events "
        "via HTTP Event Collector, and audit search-head health."
    ),
)

ext.secret(
    "splunk_connections",
    (
        "Your connected Splunk instances -- stored as a JSON array, one "
        "entry per instance, each with its own base_url and auth "
        "token/session key. Managed through connect_splunk / "
        "disconnect_splunk -- you should not need to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)

ext.secret(
    "splunk_hec_tokens",
    (
        "Your saved HTTP Event Collector tokens, one per instance -- "
        "stored as a JSON array. Managed through save_hec_token / "
        "delete_hec_token."
    ),
    required=False,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one instance connection is stored, same shape as PagerDuty
    Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("splunk_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Splunk instance(s) connected." if count
            else "Not connected yet -- run connect_splunk."
        ),
    }
