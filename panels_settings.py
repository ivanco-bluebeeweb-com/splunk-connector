"""The single 'App settings' screen (center slot) -- connection management
(disconnect per instance) and HEC token management (save/list/delete) for
Splunk Connector. Same convention as PagerDuty Connector's panels_settings.py.

Per ~/UI_INTERFACE_STANDARD.md: the left sidebar never wraps the connect
form in a Card, and disconnect / secondary secret management (never
exposed in the sidebar itself) live here. The one secondary "App settings"
button sits LAST at the bottom of the sidebar. All setup instructions for
adding a HEC token live only here -- not duplicated in the sidebar.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from handlers_connection import _load_connections, _load_hec_tokens


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"),
        node,
    ])


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("base_url", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(c.get("base_url", ""), variant="caption"),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_splunk", {"connection_id": c.get("id")}),
        ),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("Connections", variant="heading"),
            ui.Text("No Splunk instance connected yet.", variant="caption"),
        ])
    return ui.Stack(direction="v", gap=3, children=[
        ui.Text("Connections", variant="heading"),
        *[_connection_row(c) for c in connections],
    ])


def _hec_token_row(t: dict) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(t.get("label") or t.get("id", ""), variant="body"),
        ui.Text(f"index: {t.get('default_index') or '(default)'}", variant="caption"),
        ui.Button(
            "Delete", variant="danger", size="sm",
            on_click=ui.Call("delete_hec_token", {"token_id": t.get("id")}),
        ),
    ])


def _hec_form(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[])
    return ui.Form(
        on_submit=ui.Call("save_hec_token"),
        children=[
            ui.Stack(direction="v", gap=3, align="stretch", children=[
                _field("Instance", ui.Select(
                    param_name="connection_id",
                    options=[{"label": c.get("label") or c.get("base_url", ""), "value": c.get("id")} for c in connections],
                )),
                _field("HEC token", ui.Password(
                    param_name="hec_token",
                    placeholder="HTTP Event Collector token (Settings > Data Inputs > HTTP Event Collector)",
                )),
                _field("Default index (optional)", ui.Input(
                    param_name="default_index",
                    placeholder="main",
                )),
                _field("Label (optional)", ui.Input(
                    param_name="label",
                    placeholder="e.g. Production HEC",
                )),
                ui.Button("Save HEC token", variant="primary"),
            ]),
        ],
    )


def _hec_section(connections: list[dict], tokens: list[dict]) -> ui.UINode:
    body = [ui.Text("HTTP Event Collector tokens", variant="heading")]
    body.append(ui.Text(
        "Separate from your management credentials -- HEC tokens only allow "
        "sending events into an index (Settings > Data Inputs > HTTP Event "
        "Collector > New Token), used by the send_event action.",
        variant="caption",
    ))
    if tokens:
        body.extend(_hec_token_row(t) for t in tokens)
    else:
        body.append(ui.Text("No HEC tokens saved yet.", variant="caption"))
    body.append(_hec_form(connections))
    return ui.Stack(direction="v", gap=3, children=body)


@ext.panel("splunk_settings", slot="center", title="Splunk -- App settings", center_overlay=True)
async def splunk_settings_panel(ctx) -> ui.UINode:
    connections = await _load_connections(ctx)
    tokens = await _load_hec_tokens(ctx)
    return ui.Stack(direction="v", gap=6, children=[
        ui.Header("Splunk -- App settings"),
        _connections_section(connections),
        ui.Divider(),
        _hec_section(connections, tokens),
    ])
