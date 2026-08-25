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

Form container is stretched full-width (align="stretch") and its Input/
Password/Select fields use native `label=`/`placeholder=` per
UI_INTERFACE_STANDARD.md's Label+Field+gap-container rule -- no separate
ui.Text label lines, no duplicated setup instructions here (the full
walkthrough lives only in the "App settings" screen / connect help).
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import splunk_client as sc
from handlers_connection import _load_connections


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
        ui.Input(
            param_name="base_url", label="Base URL",
            placeholder="https://splunk.mycompany.com:8089",
        ),
        ui.Select(
            param_name="auth_mode", label="Способ входа",
            options=[
                {"label": "Auth token", "value": "token"},
                {"label": "Логин и пароль", "value": "password"},
            ],
            value="token",
        ),
        ui.Password(
            param_name="auth_token", label="Auth token",
            placeholder="Settings > Tokens > New Token",
        ),
        ui.Input(
            param_name="username", label="Имя пользователя",
            placeholder="admin",
        ),
        ui.Password(
            param_name="password", label="Пароль",
            placeholder="Пароль пользователя Splunk",
        ),
        ui.Button("Подключить", type="submit", variant="primary", full_width=True,
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
            ui.TextArea(
                param_name="spl_query", label="SPL-запрос",
                placeholder="index=security sourcetype=auth | stats count by user",
                rows=4,
            ),
            ui.Row(gap=2, children=[
                ui.Input(param_name="earliest_time", label="С", placeholder="-24h", value="-24h"),
                ui.Input(param_name="latest_time", label="По", placeholder="now", value="now"),
            ]),
            ui.Button("Выполнить поиск", type="submit", variant="primary",
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
        return ui.Alert(title="Не удалось загрузить saved searches", message=str(exc), variant="error")
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
            empty_text="Нет сохранённых поисков",
        ),
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
        return ui.Alert(title="Не удалось загрузить индексы", message=str(exc), variant="error")
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
            empty_text="Нет индексов",
        ),
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
        return ui.Alert(title="Не удалось загрузить пользователей/роли", message=str(exc), variant="error")
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
                empty_text="Нет пользователей",
            ),
        },
        {
            "label": "Roles",
            "content": ui.DataTable(
                columns=[
                    ui.DataColumn("name", "Роль"),
                    ui.DataColumn("capabilities", "Возможности"),
                ],
                rows=role_rows,
                empty_text="Нет ролей",
            ),
        },
    ])
