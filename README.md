# Genie Embed

Local Dash app that embeds a Databricks AI/BI Genie Space.

**Workspace:** `https://adb-7405616034846735.15.azuredatabricks.net`

---

## 1. Deploy the Genie App to the workspace

The `genie_space/` submodule is a Dash app that serves the Genie conversation UI. Deploy it as a Databricks App so the local wrapper can iframe it.

Upload the submodule source to the workspace:

```bash
databricks workspace import-dir genie_space/genie_space \
  /Workspace/Users/$USER/genie_space --overwrite \
  --profile <your-profile>
```

Then in the workspace UI:

1. **Compute > Apps > Create App** — name it (e.g. `genie-space-embed`).
2. Set source path to `/Workspace/Users/<you>/genie_space`.
3. Under **Resources**, add:
   - `genie-space` → your Genie Space ID
   - `serving-endpoint` → a Foundation Model endpoint (for "Generate Insights")
4. **Deploy**.
5. Grant the app's service principal `CAN RUN` on the Genie Space.
6. Copy the deployed app URL (e.g. `https://genie-space-embed-<id>.azure.databricksapps.com`).

The app uses **on-behalf-of (OBO) auth** — Genie API calls run as the logged-in user, so no separate table grants for the service principal are needed. Users just need their own access to the underlying data.

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

```bash
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
