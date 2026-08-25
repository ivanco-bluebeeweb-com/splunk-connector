"""Splunk HTTP client -- two distinct auth surfaces (REST management API,
HTTP Event Collector), one shared request helper per surface. Uses the
platform's own `ctx.http` (async), never `requests`. Same ClientFail/fail()
shape as pagerduty_client.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


class ClientFail(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.message = message
        self.status = status


def fail(message: str, status: int = 0):
    raise ClientFail(message, status)


def _auth_header(conn: dict) -> dict:
    token = conn.get("auth_token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    # session key mode: caller must have exchanged username/password already
    session_key = conn.get("session_key", "")
    if session_key:
        return {"Authorization": f"Splunk {session_key}"}
    fail("No auth token or session key available for this connection.")
    return {}


async def _request(ctx, conn: dict, method: str, path: str, *, params: dict | None = None,
                    data: dict | None = None) -> dict:
    base_url = conn.get("base_url", "").rstrip("/")
    if not base_url:
        fail("Missing base_url for this Splunk connection.")
    url = f"{base_url}{path}"
    qp = dict(params or {})
    qp["output_mode"] = "json"
    headers = _auth_header(conn)
    try:
        resp = await ctx.http.request(method, url, headers=headers, params=qp, data=data, timeout=30)
    except Exception as exc:  # network/SSRF-guard errors surface here
        fail(f"Request to Splunk failed: {exc}")
        return {}
    if resp.status_code == 401:
        fail("Splunk rejected the credentials (401) -- token/session may have expired.", 401)
    if resp.status_code == 403:
        fail("Splunk denied this action (403) -- the account may lack the required capability.", 403)
    if resp.status_code >= 400:
        fail(f"Splunk returned {resp.status_code}: {resp.text[:300]}", resp.status_code)
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}


async def get_session_key(ctx, base_url: str, username: str, password: str) -> str:
    """Exchange username/password for a session key via /services/auth/login."""
    base_url = base_url.rstrip("/")
    try:
        resp = await ctx.http.request(
            "POST", f"{base_url}/services/auth/login",
            data={"username": username, "password": password, "output_mode": "json"},
            timeout=30,
        )
    except Exception as exc:
        fail(f"Could not reach Splunk to authenticate: {exc}")
        return ""
    if resp.status_code == 401:
        fail("Invalid Splunk username/password.", 401)
    if resp.status_code >= 400:
        fail(f"Splunk login failed ({resp.status_code}): {resp.text[:300]}", resp.status_code)
    try:
        body = resp.json()
        return body.get("sessionKey", "")
    except Exception:
        fail("Splunk login response did not contain a session key.")
        return ""


async def validate_connection(ctx, conn: dict) -> dict:
    """Cheap validation call -- GET /services/server/info."""
    return await _request(ctx, conn, "GET", "/services/server/info")


# ── Search jobs ─────────────────────────────────────────────────────────

async def dispatch_search(ctx, conn: dict, spl_query: str, earliest_time: str, latest_time: str) -> dict:
    q = spl_query.strip()
    if not q.lower().startswith("search") and not q.startswith("|"):
        q = f"search {q}"
    return await _request(
        ctx, conn, "POST", "/services/search/jobs",
        data={"search": q, "earliest_time": earliest_time, "latest_time": latest_time},
    )


async def get_search_status(ctx, conn: dict, sid: str) -> dict:
    return await _request(ctx, conn, "GET", f"/services/search/jobs/{sid}")


async def get_search_results(ctx, conn: dict, sid: str, offset: int, count: int) -> dict:
    return await _request(
        ctx, conn, "GET", f"/services/search/jobs/{sid}/results",
        params={"offset": offset, "count": count},
    )


async def cancel_search(ctx, conn: dict, sid: str) -> dict:
    return await _request(ctx, conn, "POST", f"/services/search/jobs/{sid}/control", data={"action": "cancel"})


# ── Saved searches ──────────────────────────────────────────────────────

async def list_saved_searches(ctx, conn: dict) -> dict:
    return await _request(ctx, conn, "GET", "/services/saved/searches", params={"count": 200})


async def get_saved_search(ctx, conn: dict, name: str) -> dict:
    return await _request(ctx, conn, "GET", f"/services/saved/searches/{name}")


async def create_saved_search(ctx, conn: dict, name: str, spl_query: str, cron_schedule: str) -> dict:
    data = {"name": name, "search": spl_query}
    if cron_schedule:
        data["cron_schedule"] = cron_schedule
        data["is_scheduled"] = "1"
    return await _request(ctx, conn, "POST", "/services/saved/searches", data=data)


async def update_saved_search(ctx, conn: dict, name: str, spl_query: str = "", cron_schedule: str = "") -> dict:
    data = {}
    if spl_query:
        data["search"] = spl_query
    if cron_schedule:
        data["cron_schedule"] = cron_schedule
    return await _request(ctx, conn, "POST", f"/services/saved/searches/{name}", data=data)


async def delete_saved_search(ctx, conn: dict, name: str) -> dict:
    return await _request(ctx, conn, "DELETE", f"/services/saved/searches/{name}")


async def dispatch_saved_search(ctx, conn: dict, name: str) -> dict:
    return await _request(ctx, conn, "POST", f"/services/saved/searches/{name}/dispatch")


# ── Indexes ─────────────────────────────────────────────────────────────

async def list_indexes(ctx, conn: dict) -> dict:
    return await _request(ctx, conn, "GET", "/services/data/indexes", params={"count": 200})


# ── Users / roles ───────────────────────────────────────────────────────

async def list_users(ctx, conn: dict) -> dict:
    return await _request(ctx, conn, "GET", "/services/authentication/users", params={"count": 200})


async def list_roles(ctx, conn: dict) -> dict:
    return await _request(ctx, conn, "GET", "/services/authorization/roles", params={"count": 200})


# ── HEC (separate base host/port, separate auth) ───────────────────────

async def send_hec_event(ctx, hec_base_url: str, hec_token: str, event: str, source: str,
                          sourcetype: str, index: str) -> dict:
    hec_base_url = hec_base_url.rstrip("/")
    payload = {"event": event, "source": source, "sourcetype": sourcetype}
    if index:
        payload["index"] = index
    try:
        resp = await ctx.http.request(
            "POST", f"{hec_base_url}/services/collector/event",
            headers={"Authorization": f"Splunk {hec_token}"},
            json=payload, timeout=30,
        )
    except Exception as exc:
        fail(f"Could not reach Splunk HEC: {exc}")
        return {}
    if resp.status_code >= 400:
        fail(f"HEC rejected the event ({resp.status_code}): {resp.text[:300]}", resp.status_code)
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text}
