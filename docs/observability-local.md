# Local observability setup

This guide connects the localhost-bound API to local metrics, alerting, and trace viewing. Prometheus and Grafana remain separately installed or run free and open-source tools. A dedicated Docker Compose file runs Jaeger locally as an OTLP receiver and trace viewer.

## Configuration files

- `deployment/observability/prometheus.yml` scrapes `127.0.0.1:8000/metrics` every 15 seconds. It sends the API bearer key from `deployment/observability/secrets/api_key`.
- `deployment/observability/alerts/eu-ai-act-sandbox-api.rules.yml` defines warning alerts for a continuously unavailable API scrape target and repeated retrieval capacity rejections.
- `deployment/observability/jaeger.compose.yml` runs Jaeger 2.22.0 with its UI and OTLP/HTTP receiver bound to localhost.
- `deployment/observability/grafana/provisioning/datasources/prometheus.yml` registers a default Prometheus data source at `http://127.0.0.1:9090`.
- `deployment/observability/grafana/provisioning/dashboards/provider.yml` configures file-based dashboard provisioning. Set `options.path` to the absolute directory containing the JSON dashboard in your Grafana installation or container.
- `deployment/observability/grafana/dashboards/eu-ai-act-sandbox-api.json` contains the dashboard. It shows target availability, active retrieval count, capacity rejections over the previous hour, the number of firing API alerts, HTTP request rate by status, and P95 request latency by route.

## Prepare the scrape credential

Prometheus must send the same API key used by the application. From the repository root in PowerShell, create the local secret file and keep the environment value for the API process:

```powershell
$apiKey = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))").Trim()
$env:API_KEY = $apiKey
New-Item -ItemType Directory -Force deployment/observability/secrets | Out-Null
Set-Content -NoNewline -Encoding ascii -Path deployment/observability/secrets/api_key -Value $apiKey
Remove-Variable apiKey
```

The secrets directory is ignored by Git. Restrict its filesystem permissions to the account running Prometheus. Do not put the key in the Prometheus YAML, dashboard JSON, or a committed environment file.

Start the API using the documented command and keep it bound to `127.0.0.1`. Start Prometheus from the repository root with this configuration so its relative `credentials_file` path resolves correctly:

```powershell
& 'C:\path\to\prometheus.exe' `
  --config.file=deployment/observability/prometheus.yml `
  --web.listen-address=127.0.0.1:9090 `
  --storage.tsdb.path=data/prometheus
```

Prometheus will scrape the authenticated endpoint. Its `up{job="eu-ai-act-sandbox-api"}` series should be `1` when scraping succeeds. If Prometheus runs in a container, `127.0.0.1` refers to that container. Change the target to the API's reachable address on a private container network, and do not publish the API port broadly.
## Alert rules

The Prometheus configuration loads the API alert rule file. `EuAiActSandboxApiTargetDown` becomes firing after the target remains down for one minute. `EuAiActSandboxRetrievalCapacityRejections` becomes firing when at least three rejections are observed within five minutes and that expression remains true for two minutes. These are initial warning thresholds for local development and should be tuned from observed workload and operational impact.

Prometheus evaluates and displays these alerts in its Alerts page. Grafana also shows the current count of firing API alerts on the dashboard. The rules do not send email, chat, or paging notifications by themselves. Delivering notifications requires an Alertmanager installation and receiver configuration, which is intentionally outside this local configuration section.

## Provision Grafana

Copy or mount the datasource provisioning file into Grafana's `provisioning/datasources` directory. Copy or mount the dashboard provider file into `provisioning/dashboards`, then set the provider's `options.path` to the absolute dashboard directory and mount `eu-ai-act-sandbox-api.json` there. Grafana reads provisioned data sources and file-based dashboards from those configured paths. The Prometheus URL assumes Grafana runs directly on the same host. If Grafana runs in a container, use the Prometheus service name or another address reachable from that container.

After Grafana starts, open its Dashboards page and select the **EU AI Act Sandbox** folder. The provisioned dashboard is managed from the JSON file, so make lasting edits in the file and reload the dashboard rather than relying on UI-only changes.

The metrics currently have no tenant or user labels. Do not add raw URLs, query text, API keys, or caller identity as Prometheus labels.

## Metric panels

| Panel | Prometheus expression |
|---|---|
| API target up | `up{job="eu-ai-act-sandbox-api"}` |
| Retrievals in flight | `retrieval_requests_in_flight{job="eu-ai-act-sandbox-api"}` |
| Capacity rejections, last hour | `sum(increase(retrieval_capacity_rejections_total{job="eu-ai-act-sandbox-api"}[1h]))` |
| Firing API alerts | `sum(ALERTS{alertstate="firing",service="eu-ai-act-sandbox-api"}) or vector(0)` |
| HTTP request rate by status | `sum by (status_code) (rate(http_server_requests_total{job="eu-ai-act-sandbox-api",route!="/metrics"}[5m]))` |
| P95 request latency by route | `histogram_quantile(0.95, sum by (le, route) (rate(http_server_request_duration_seconds_bucket{job="eu-ai-act-sandbox-api",route!="/metrics"}[5m])))` |

Prometheus uses `authorization.credentials_file` for the bearer credential, as documented in its [configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/configuration/). Grafana's datasource and dashboard files use its [provisioning system](https://grafana.com/docs/grafana/latest/administration/provisioning/).


## Local Jaeger trace viewer

Jaeger provides a local UI for inspecting request and nested retrieval spans emitted by the API. This all-in-one setup uses in-memory storage, so traces disappear when the container stops. The Compose file publishes only the UI port (16686) and OTLP/HTTP port (4318), and binds both to 127.0.0.1. Keep these ports local unless access controls are added.

Start Jaeger from the repository root:

```powershell
docker compose -f deployment/observability/jaeger.compose.yml up -d
```

Install optional tracing dependencies if needed:

```powershell
uv sync --extra api --extra embeddings --extra tracing --extra otlp
```

In the PowerShell session used for the API, select Jaeger as the OTLP destination and start the API:

```powershell
$env:OTEL_TRACES_EXPORTER = "otlp"
$env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = "http://127.0.0.1:4318/v1/traces"
$env:OTEL_SERVICE_NAME = "eu-ai-act-sandbox-api"
uv run uvicorn eu_ai_act_sandbox.api.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:16686 and select the eu-ai-act-sandbox-api service. A call to /health/live confirms the server span path. To see nested retrieval, embedding, backend, and ranking spans, send a valid authenticated retrieval request. The spans do not contain query text or retrieved passages. Stop Jaeger with docker compose -f deployment/observability/jaeger.compose.yml down.


