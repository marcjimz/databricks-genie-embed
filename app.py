import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import yaml
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ──────────────────────────────────────────────
WORKSPACE_HOST = os.getenv(
    "DATABRICKS_HOST", "adb-7405616034846735.15.azuredatabricks.net"
)
GENIE_APP_URL = os.getenv("GENIE_APP_URL", "")


def _ws_url():
    h = WORKSPACE_HOST.rstrip("/")
    return h if h.startswith("http") else f"https://{h}"


# ─── Auth & Discovery ───────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _client is None:
        from databricks.sdk import WorkspaceClient

        _client = WorkspaceClient(host=_ws_url())
    return _client


def check_auth():
    """Verify SDK credentials work against the workspace."""
    try:
        w = _get_client()
        user = w.current_user.me()
        return True, user.display_name or user.user_name
    except Exception as exc:
        return False, str(exc)


def discover_spaces():
    """Load spaces from config.yaml, then try workspace API."""
    spaces = []

    # 1. config.yaml
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f) or {}
            for s in cfg.get("genie_spaces", []):
                if s.get("id") and not s["id"].upper().startswith("YOUR"):
                    spaces.append(s)
    except FileNotFoundError:
        pass

    # 2. Workspace API (best-effort)
    try:
        w = _get_client()
        resp = w.api_client.do("GET", "/api/2.0/genie/spaces")
        known = {s["id"] for s in spaces}
        if isinstance(resp, dict):
            for item in resp.get("spaces", []):
                sid = item.get("space_id", "")
                if sid and sid not in known:
                    spaces.append(
                        {"id": sid, "name": item.get("title", f"Space {sid[:12]}")}
                    )
    except Exception:
        pass

    return spaces


# ─── Startup ────────────────────────────────────────────────────
print(f"[genie-embed] workspace : {_ws_url()}")
auth_ok, auth_user = check_auth()
print(
    f"[genie-embed] auth      : {'OK \u2014 ' + auth_user if auth_ok else 'FAILED \u2014 ' + auth_user}"
)

genie_spaces = discover_spaces()
print(f"[genie-embed] spaces    : {len(genie_spaces)} configured")
for s in genie_spaces:
    print(f"               \u2022 {s['name']}  ({s['id']})")


# ─── Dash App ───────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Intermountain Health | Data Assistant",
)


def _embed_url(space_id):
    """Build the iframe src for a given Genie Space."""
    if GENIE_APP_URL:
        # Find space name from discovered spaces
        space_name = next(
            (s["name"] for s in genie_spaces if s["id"] == space_id),
            "Data Assistant",
        )
        params = urlencode({"space_id": space_id, "space_name": space_name})
        return f"{GENIE_APP_URL.rstrip('/')}?{params}"
    return f"{_ws_url()}/explore/genie/{space_id}"


app.layout = html.Div(
    [
        # ── Header ── matches intermountainhealthcare.org
        html.Header(
            html.Div(
                [
                    # Logo (includes "Intermountain Health" wordmark)
                    html.A(
                        html.Img(
                            src="/assets/ih_logo_light.png", className="ih-logo"
                        ),
                        href="https://intermountainhealthcare.org",
                        target="_blank",
                        className="header-brand",
                    ),
                    # Right side controls
                    html.Div(
                        [
                            # Auth badge
                            html.Div(
                                [
                                    html.Div(
                                        className="status-dot "
                                        + (
                                            "connected"
                                            if auth_ok
                                            else "disconnected"
                                        )
                                    ),
                                    html.Span(
                                        auth_user
                                        if auth_ok
                                        else "Not authenticated",
                                        className="status-label",
                                    ),
                                ],
                                className="auth-badge",
                            ),
                            # Divider
                            html.Div(className="header-divider"),
                            # Space selector
                            html.Div(
                                dcc.Dropdown(
                                    id="space-select",
                                    options=[
                                        {"label": s["name"], "value": s["id"]}
                                        for s in genie_spaces
                                    ],
                                    value=(
                                        genie_spaces[0]["id"]
                                        if genie_spaces
                                        else None
                                    ),
                                    placeholder="Select Genie Space\u2026",
                                    clearable=False,
                                ),
                                className="dropdown-wrapper",
                            ),
                            # Refresh
                            html.Button(
                                "\u21bb",
                                id="refresh-btn",
                                className="refresh-btn",
                                title="Reload",
                            ),
                        ],
                        className="header-controls",
                    ),
                ],
                className="header-inner",
            ),
            className="app-header",
        ),
        # ── Main ──
        html.Div(
            [
                html.Iframe(id="genie-frame", className="genie-iframe"),
                html.Div(
                    [
                        html.Div(className="empty-icon"),
                        html.H3("Welcome"),
                        html.P(
                            "Select a Genie Space above to start exploring data with AI."
                        ),
                    ]
                    + (
                        [
                            html.A(
                                "Open workspace \u2192",
                                href=_ws_url(),
                                target="_blank",
                                className="workspace-link",
                            )
                        ]
                        if not genie_spaces
                        else []
                    ),
                    id="empty-state",
                    className="empty-state",
                ),
            ],
            className="app-main",
        ),
        # ── Footer ──
        html.Footer(
            [
                html.Span("Powered by "),
                html.Strong("Databricks AI/BI Genie"),
                html.Span(f"  \u00b7  {_ws_url()}", className="footer-dim"),
            ],
            className="app-footer",
        ),
        # Stores
        dcc.Store(id="reload-tick", data=0),
    ],
    className="app-root",
)


# ─── Callbacks ──────────────────────────────────────────────────
@app.callback(
    Output("reload-tick", "data"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def _tick(n):
    return n or 0


@app.callback(
    [
        Output("genie-frame", "src"),
        Output("genie-frame", "style"),
        Output("empty-state", "style"),
    ],
    [Input("space-select", "value"), Input("reload-tick", "data")],
)
def _update(space_id, _):
    if not space_id:
        return "", {"display": "none"}, {}
    return _embed_url(space_id), {}, {"display": "none"}


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
