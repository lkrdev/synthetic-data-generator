---
name: vertex-ai
description: Use when configuring, authenticating, or troubleshooting the Vertex AI (Google Cloud) model provider for Data Designer — including Application Default Credentials (ADC), project/region setup, and verifying connectivity before generating data.
license: Apache-2.0
metadata:
  owner: lkr.dev
---

# Goal

Get Data Designer generating data through **Vertex AI on Google Cloud** using the
`vertex` provider type, which authenticates with **Application Default
Credentials (ADC)** — no API keys.

There are two independent things to get right:

1. **Credentials (identity/token)** — provided by ADC, resolved automatically.
2. **`project` and `location`** — Data Designer config values (NOT part of ADC).

Keep them separate in your head; most setup problems come from conflating them.

# Setup

## 1. Authenticate with ADC (credentials)

Run once per machine/user; the token is then picked up automatically by any
process (including IDE-spawned terminals) that runs as you:

```bash
gcloud auth application-default login
```

Verify a token can be minted:

```bash
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK"
```

Notes:
- No environment variable is required for this — `google-auth` reads the
  well-known ADC file (`~/.config/gcloud/application_default_credentials.json`).
- A service-account key file via `GOOGLE_APPLICATION_CREDENTIALS` also works, but
  ADC login is preferred for local/IDE use.
- Ensure the authenticated principal has the **Vertex AI User** role
  (`roles/aiplatform.user`) on the target project.

## 2. Set project and region (config)

`project` is **required**; `location` defaults to `us-central1`. Resolution order
is **explicit config value > environment variable > default**. For an IDE/agent
workflow that must work "from any shell", prefer the environment variables — they
match the Google Cloud / Vertex SDK conventions:

```bash
export GOOGLE_CLOUD_PROJECT="my-gcp-project"
export GOOGLE_CLOUD_LOCATION="us-central1"   # optional; omit for the default
```

- `GOOGLE_CLOUD_LOCATION` alone does **not** satisfy the required-project check.
- Use `location="global"` (or `GOOGLE_CLOUD_LOCATION=global`) for the global
  endpoint; any other value produces a regional endpoint.

## 3. Configure the provider

Pick ONE of these; they are equivalent.

**Python (relies on env fallback):**
```python
import data_designer.config as dd

provider = dd.ModelProvider(name="vertex", provider_type="vertex")  # project/location from env
model = dd.ModelConfig(alias="vertex-text", model="google/gemini-2.5-flash", provider="vertex")
```

**Python (explicit, overrides env):**
```python
provider = dd.ModelProvider(
    name="vertex", provider_type="vertex",
    project="my-gcp-project", location="us-central1",
)
```

**Providers YAML** (`$DATA_DESIGNER_HOME/model_providers.yaml`, persistent):
```yaml
model_providers:
  - name: vertex
    provider_type: vertex
    project: my-gcp-project      # or omit to use GOOGLE_CLOUD_PROJECT
    location: us-central1        # or omit to use GOOGLE_CLOUD_LOCATION / default
```

**CLI form:** `data-designer providers add` — leave `endpoint` blank for `vertex`;
fill `project`/`location` (or leave blank to use the env vars).

# Verify before generating

Always probe connectivity before a real run:

```python
dd_client = dd.DataDesigner(model_providers=[provider])
dd_client.check_models(config_builder)   # tiny live call per referenced alias
```

Or from the CLI, run a small `preview` first. A green `check_models` confirms
credentials, project, region, and model access are all correct.

# Troubleshooting

- **`requires a project`** — neither an explicit `project` nor
  `GOOGLE_CLOUD_PROJECT` is set. Export it or pass it to `ModelProvider`.
- **`ModelAuthenticationError` / ADC not found** — run
  `gcloud auth application-default login`; confirm with
  `gcloud auth application-default print-access-token`.
- **403 / PERMISSION_DENIED** — the principal lacks `roles/aiplatform.user` on
  the project, or `project` points at the wrong project. Note the endpoint uses
  the **configured** `project`, not the project baked into your ADC.
- **404 / model not found** — the `model` id isn't available in that
  `location`; try `location="global"` or a region where the model is served.
- **Wrong region used** — check `GOOGLE_CLOUD_LOCATION`; an explicit
  `location=` on the provider overrides it.

# Reference

- Provider validation + endpoint derivation:
  `packages/data-designer-config/src/data_designer/config/models.py`
  (`ModelProvider._resolve_endpoint`, `build_vertex_openai_endpoint`).
- ADC token provider:
  `packages/data-designer-engine/src/data_designer/engine/models/clients/adapters/gcp_credentials.py`.
- Env-var names: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
  (`packages/data-designer-config/src/data_designer/config/utils/constants.py`).
