"""Panel UI -- connections list/connect form + search / saved searches /
indexes quick view in the left sidebar and main center panel.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as PagerDuty
Connector's / MuleSoft Connector's panels.py).

Every section is a plain ui.Stack, content stacked vertically and
left-aligned, sections separated by ui.Divider() -- no Card
border/background/shadow anywhere in this slot. Disconnect and HEC token
management live only in the "App settings" screen (panels_settings.py).
The one secondary "App settings" button is always the LAST element at the
bottom of the sidebar.

Form container is stretched full-width (align="stretch") and every Input/
Password/Select/TextArea field carries its own visible label via the
_field() wrapper below (Input/Select/Password/TextArea themselves take
no `label=` kwarg) plus a contextually specific placeholder, per
UI_INTERFACE_STANDARD.md's Label+Field+gap-container rule -- no
duplicated setup instructions here (the full walkthrough lives only in
the "App settings" screen / connect help).
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import splunk_client as sc
from handlers_connection import _load_connections


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"),
        node,
    ])


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__splunk_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("base_url", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(c.get("base_url", ""), variant="caption"),
    ])


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        _field("Base URL", ui.Input(
            param_name="base_url",
            placeholder="https://splunk.mycompany.com:8089",
        )),
        _field("Способ входа", ui.Select(
            param_name="auth_mode",
            options=[
                {"label": "Auth token", "value": "token"},
                {"label": "Логин и пароль", "value": "password"},
            ],
            value="token",
        )),
        _field("Auth token", ui.Password(
            param_name="auth_token",
            placeholder="Settings > Tokens > New Token",
        )),
        _field("Имя пользователя", ui.Input(
            param_name="username",
            placeholder="admin",
        )),
        _field("Пароль", ui.Password(
            param_name="password",
            placeholder="Пароль пользователя Splunk",
        )),
        ui.Button("Подключить", variant="primary", full_width=True,
                  on_click=ui.Call("connect_splunk")),
    ])


@ext.panel("splunk_main", slot="left", title="Splunk", icon="🔎")
async def splunk_sidebar(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    children: list[ui.UINode] = []

    if not connections:
        children.append(ui.Text("Splunk не подключён", variant="heading"))
        children.append(_connect_form())
    else:
        children.append(ui.Text("Подключения", variant="heading"))
        for c in connections:
            children.append(_connection_row(c))
        children.append(ui.Divider())
        children.append(ui.Text("Разделы", variant="heading"))
        children.append(ui.ListItem(id="search", title="Search", icon="search", on_click=ui.Call("__panel__splunk_search")))
        children.append(ui.ListItem(id="saved", title="Saved Searches", icon="bell", on_click=ui.Call("__panel__splunk_saved_searches")))
        children.append(ui.ListItem(id="indexes", title="Indexes", icon="database", on_click=ui.Call("__panel__splunk_indexes")))
        children.append(ui.ListItem(id="users", title="Users & Roles", icon="users", on_click=ui.Call("__panel__splunk_users")))

    children.append(ui.Divider())
    children.append(_settings_button())

    return ui.Stack(direction="v", gap=3, align="start", children=children)


@ext.panel("splunk_search", slot="center", title="Search", icon="🔎", center_overlay=True)
async def splunk_search_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Подключите Splunk, чтобы начать поиск", icon="search")
    return ui.Stack(direction="v", gap=4, children=[
        ui.Header("Search"),
        ui.Stack(direction="v", gap=3, align="stretch", children=[
            _field("SPL-запрос", ui.TextArea(
                param_name="spl_query",
                placeholder="index=security sourcetype=auth | stats count by user",
                rows=4,
            )),
            ui.Row(gap=2, children=[
                _field("С", ui.Input(param_name="earliest_time", placeholder="-24h", value="-24h")),
                _field("По", ui.Input(param_name="latest_time", placeholder="now", value="now")),
            ]),
            ui.Button("Выполнить поиск", variant="primary",
                      on_click=ui.Call("dispatch_search")),
        ]),
    ])


@ext.panel("splunk_saved_searches", slot="center", title="Saved Searches", icon="🔔", center_overlay=True)
async def splunk_saved_searches_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Подключите Splunk", icon="bell")
    conn = connections[0]
    try:
        body = await sc.list_saved_searches(ctx, conn)
        entries = body.get("entry", [])
    except sc.ClientFail as exc:
        return ui.Alert(title="Не удалось загрузить saved searches", message=str(exc), type="error")
    rows = [
        {
            "name": e.get("name", ""),
            "cron_schedule": (e.get("content") or {}).get("cron_schedule", ""),
            "has_alert_action": "да" if ((e.get("content") or {}).get("actions") or "").strip() else "нет",
            "disabled": "да" if (e.get("content") or {}).get("disabled") else "нет",
        }
        for e in entries
    ]
    return ui.Stack(direction="v", gap=3, children=[
        ui.Header("Saved Searches"),
        ui.DataTable(
            columns=[
                ui.DataColumn("name", "Название"),
                ui.DataColumn("cron_schedule", "Расписание"),
                ui.DataColumn("has_alert_action", "Alert action"),
                ui.DataColumn("disabled", "Отключён"),
            ],
            rows=rows,
        ) if rows else ui.Empty(message="Нет сохранённых поисков", icon="bell"),
    ])


@ext.panel("splunk_indexes", slot="center", title="Indexes", icon="🗄️", center_overlay=True)
async def splunk_indexes_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Подключите Splunk", icon="database")
    conn = connections[0]
    try:
        body = await sc.list_indexes(ctx, conn)
        entries = body.get("entry", [])
    except sc.ClientFail as exc:
        return ui.Alert(title="Не удалось загрузить индексы", message=str(exc), type="error")
    rows = []
    for e in entries:
        c = e.get("content", {})
        cur = int(c.get("currentDBSizeMB", 0) or 0)
        mx = int(c.get("maxTotalDataSizeMB", 0) or 0)
        rows.append({
            "name": e.get("name", ""),
            "current_size_mb": cur,
            "max_size_mb": mx,
            "near_quota": "да" if mx and cur >= 0.9 * mx else "нет",
        })
    return ui.Stack(direction="v", gap=3, children=[
        ui.Header("Indexes"),
        ui.DataTable(
            columns=[
                ui.DataColumn("name", "Индекс"),
                ui.DataColumn("current_size_mb", "Размер (MB)"),
                ui.DataColumn("max_size_mb", "Квота (MB)"),
                ui.DataColumn("near_quota", "Близко к квоте"),
            ],
            rows=rows,
        ) if rows else ui.Empty(message="Нет индексов", icon="database"),
    ])


@ext.panel("splunk_users", slot="center", title="Users & Roles", icon="👥", center_overlay=True)
async def splunk_users_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    if not connections:
        return ui.Empty(message="Подключите Splunk", icon="users")
    conn = connections[0]
    try:
        u_body = await sc.list_users(ctx, conn)
        r_body = await sc.list_roles(ctx, conn)
    except sc.ClientFail as exc:
        return ui.Alert(title="Не удалось загрузить пользователей/роли", message=str(exc), type="error")
    user_rows = []
    for e in u_body.get("entry", []):
        c = e.get("content", {})
        user_rows.append({
            "username": e.get("name", ""),
            "real_name": c.get("realname", ""),
            "roles": ", ".join(c.get("roles", []) or []),
            "email": c.get("email", ""),
        })
    role_rows = []
    for e in r_body.get("entry", []):
        c = e.get("content", {})
        role_rows.append({
            "name": e.get("name", ""),
            "capabilities": ", ".join((c.get("capabilities", []) or [])[:5]),
        })
    return ui.Tabs(tabs=[
        {
            "label": "Users",
            "content": ui.DataTable(
                columns=[
                    ui.DataColumn("username", "Пользователь"),
                    ui.DataColumn("real_name", "Имя"),
                    ui.DataColumn("roles", "Роли"),
                    ui.DataColumn("email", "Email"),
                ],
                rows=user_rows,
            ) if user_rows else ui.Empty(message="Нет пользователей", icon="users"),
        },
        {
            "label": "Roles",
            "content": ui.DataTable(
                columns=[
                    ui.DataColumn("name", "Роль"),
                    ui.DataColumn("capabilities", "Возможности"),
                ],
                rows=role_rows,
            ) if role_rows else ui.Empty(message="Нет ролей", icon="users"),
        },
    ])
