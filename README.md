# Genie Embed

Local Dash app that embeds a Databricks AI/BI Genie Space via iframe, pointed at a deployed Databricks App.

**Workspace:** `https://adb-7405616034846735.15.azuredatabricks.net`

---

## Authorization Architecture

The deployed Genie app (`genie_space/`) uses two authorization modes:

### Service Principal (SP) 

Used for APIs whose required OAuth scopes are **not available** to Databricks Apps OBO tokens.

| What | Why SP? |
|------|---------|
| **Genie Space metadata** (title, sample questions) | `GET /api/2.0/genie/spaces/{id}` requires the `genie` scope — not grantable to OBO tokens |
| **LLM insights** (model serving) | Serving endpoint API requires the `model-serving` scope — not grantable to OBO tokens |

**SP permissions required:**

| Resource | Permission |
|----------|-----------|
| Genie Space | `CAN_EDIT` |
| UC Catalog | `USE CATALOG` |
| UC Schema | `USE SCHEMA` |
| UC Tables (underlying the Genie Space) | `SELECT` |
| Serving Endpoint | `CAN_QUERY` |

### On-Behalf-Of (OBO)

Used for Genie query execution — runs as the logged-in user so data access respects their UC permissions.

- Auth: OBO token from `X-Forwarded-Access-Token` request header
- App OAuth scopes (in `app.yaml`): `genie`, `sql`

**User permissions required:**

| Resource | Permission |
|----------|-----------|
| Genie Space | `CAN_RUN` (or higher) |
| UC Tables (underlying the Genie Space) | `SELECT` |

> **TODO:** When `genie` and `model-serving` OAuth scopes are formally added to Databricks Apps, migrate metadata and insights to OBO auth and remove the SP dependency.

---

## 1. Deploy the Genie App

The `genie_space/` submodule is a Dash app that serves the Genie conversation UI. Deploy it as a Databricks App so the local wrapper can iframe it.

```bash
databricks workspace import-dir genie_space/genie_space \
  /Workspace/Users/$USER/genie_space --overwrite \
  --profile <your-profile>
```

Then in the workspace UI:

1. **Compute > Apps > Create App** — name it (e.g. `genie-space-embed`).
2. Set source path to `/Workspace/Users/<you>/genie_space`.
3. Under **Resources**, add:
   - `genie-space` → your Genie Space ID (SP gets `CAN_EDIT`)
   - `serving-endpoint` → a Foundation Model endpoint (SP gets `CAN_QUERY`)
4. **Deploy**.
5. Grant the SP access to UC tables:
   ```sql
   GRANT USE CATALOG ON CATALOG <catalog> TO `<sp-name>`;
   GRANT USE SCHEMA ON SCHEMA <catalog>.<schema> TO `<sp-name>`;
   GRANT SELECT ON SCHEMA <catalog>.<schema> TO `<sp-name>`;
   ```
6. Grant end users `CAN_RUN` on the Genie Space and `SELECT` on the underlying UC tables.

## 2. Authenticate locally

```bash
az login
```

The Databricks SDK picks up your Azure AD session automatically — no tokens needed.

## 3. Configure & run

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` — set `GENIE_APP_URL` to the deployed app URL from step 1:

```
DATABRICKS_HOST=adb-7405616034846735.15.azuredatabricks.net
GENIE_APP_URL=https://genie-space-embed-7405616034846735.15.azure.databricksapps.com
```

Run:

```bash
python app.py
```

Open [http://localhost:8050](http://localhost:8050).

Log into the Databricks workspace in the same browser so the iframe can authenticate.

> The header shows a green dot and your username when SDK auth is working.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Red dot / "Not authenticated" | Run `az login` and restart the app |
| iframe blank or login redirect | Log into the workspace in the same browser first |
| No spaces in dropdown | Add Space IDs to `config.yaml` manually |
| 403 "Invalid scope: genie" on queries | Ensure `app.yaml` has `authorization.scopes: [genie, sql]` |
| "Generate Insights" scope error | Ensure the SP has `CAN_QUERY` on the serving endpoint resource |
