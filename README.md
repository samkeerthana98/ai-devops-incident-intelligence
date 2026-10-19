# AI DevOps Incident Intelligence

A lightweight Flask application for simulating DevOps incidents, retrieving
relevant runbooks, and generating AI-powered incident analysis using a local
Ollama model.

## Features

- **Incident Reporting** — Create and list simulated `http_500` and `high_latency`
  incidents via a REST API or a web dashboard.
- **AI Analysis** — Request structured incident analysis (summary, likely cause,
  evidence, recommendations) from a local Ollama model with runbook retrieval.
- **Runbook Retrieval** — Keyword-based retrieval selects the most relevant
  runbook to provide context for AI analysis. No vector database required.
- **Dashboard** — Responsive HTML/CSS dashboard for creating incidents and
  viewing AI analysis results.
- **Docker** — Production-ready Dockerfile with non-root user and gunicorn.
- **Helm Chart** — Kubernetes deployment with secure container settings,
  resource limits, and health probes.
- **CI/CD** — GitHub Actions workflow running pytest and Trivy security scans.
- **GitOps** — Argo CD Application manifest for automated Kubernetes deployment
  with sync, prune, and self-heal.

## Architecture

```mermaid
graph TD
    A[User / Browser] -->|HTTP| B[Flask App :5000]
    B --> C[In-Memory Incident Store]
    B -->|GET /dashboard| D[Jinja2 Template + CSS/JS]
    B -->|POST /api/incidents/:id/analyze| E[Retrieval Module]
    E -->|Keyword match| F[Runbooks /runbooks/*.md]
    E -->|Runbook context| G[Ollama Client]
    G -->|HTTP POST /api/generate| H[Ollama LLM :11434]
    H -->|Structured JSON| G
    G -->|summary, cause, evidence, recs| B
    B -->|JSON / HTML| A

    subgraph CI/CD
        I[GitHub Push / PR] --> J[GitHub Actions]
        J -->|pytest| K[Test Suite]
        J -->|Trivy FS scan| L[Security Scan]
        L -->|SARIF| M[GitHub Security Tab]
    end

    subgraph Kubernetes
        N[Helm Chart] --> O[Deployment]
        O --> P[Pod: Flask + gunicorn]
        P --> Q[Service ClusterIP]
        N --> R[ServiceAccount]
        N --> S[Health Probes]
    end

    subgraph GitOps
        T[Git Repository main] -->|Argo CD Application| U[Argo CD]
        U -->|Sync + Self-Heal| N
    end
```

## Quick Start

### Prerequisites

- Python 3.12
- [Ollama](https://ollama.ai) installed locally (for AI analysis)
- Docker (optional, for containerized deployment)
- Helm 3.x (optional, for Kubernetes deployment)

### Local Development

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application (serves on 0.0.0.0:5000)
python app.py
```

### Running Tests

```bash
pytest test_app.py test_analysis.py test_dashboard.py -v
```

Tests mock the Ollama HTTP API — no running model is required.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service information (JSON) |
| GET | `/health` | Health check (JSON) |
| GET | `/api/incidents` | List all incidents |
| POST | `/api/incidents` | Create a new incident |
| POST | `/api/incidents/<id>/analyze` | Request AI analysis for an incident |
| GET | `/dashboard` | Web dashboard (HTML) |

### Creating an Incident

```bash
curl -X POST http://localhost:5000/api/incidents \
  -H "Content-Type: application/json" \
  -d '{"incident_type": "http_500", "description": "Checkout page 500 error", "severity": "high"}'
```

### Requesting Analysis

```bash
curl -X POST http://localhost:5000/api/incidents/<incident_id>/analyze
```

## Configuration

The application reads configuration from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port the Flask/gunicorn server listens on |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.2:latest` | Ollama model name |

## Docker

### Build and Run

```bash
docker build -t ai-devops-incident-intelligence .
docker run -p 5000:5000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  ai-devops-incident-intelligence
```

The Dockerfile uses `python:3.12-slim`, runs as a non-root user, and serves
with gunicorn (2 workers).

## Kubernetes Deployment with Helm

### Prerequisites

- A running Kubernetes cluster (e.g. [kind](https://kind.sigs.k8s.io/),
  minikube, or a cloud provider)
- Helm 3.x installed
- A container image pushed to a registry accessible from the cluster

### Deploy

```bash
# Install the chart
helm install incident-intelligence ./helm/ai-devops-incident-intelligence \
  --set image.repository=ghcr.io/your-org/ai-devops-incident-intelligence \
  --set image.tag=1.0.0 \
  --set env.OLLAMA_BASE_URL=http://ollama-service:11434

# Verify the deployment
kubectl get pods -l app.kubernetes.io/name=ai-devops-incident-intelligence

# Port-forward for local access
kubectl port-forward svc/incident-intelligence-ai-devops-incident-intelligence 5000:80
```

### Helm Configuration

Key values can be overridden with `--set` or a custom values file:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image.repository` | `ghcr.io/your-org/ai-devops-incident-intelligence` | Container image repository |
| `image.tag` | `1.0.0` | Container image tag |
| `replicaCount` | `1` | Number of pod replicas |
| `service.type` | `ClusterIP` | Kubernetes Service type |
| `service.port` | `80` | Service port |
| `env.PORT` | `5000` | Container listen port |
| `env.OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama URL |
| `env.OLLAMA_MODEL` | `llama3.2:latest` | Ollama model name |
| `resources.requests.cpu` | `100m` | CPU request |
| `resources.requests.memory` | `128Mi` | Memory request |
| `resources.limits.cpu` | `500m` | CPU limit |
| `resources.limits.memory` | `256Mi` | Memory limit |

### Validate the Chart

```bash
# Lint the chart
helm lint ./helm/ai-devops-incident-intelligence

# Render templates without deploying
helm template ./helm/ai-devops-incident-intelligence
```

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and
pull request:

1. **Test job** — Installs dependencies from `requirements.txt` and runs the
   full pytest suite (`test_app.py`, `test_analysis.py`, `test_dashboard.py`).
2. **Trivy security scan** — Scans the repository filesystem for HIGH and
   CRITICAL vulnerabilities, secrets, and misconfigurations. Results are
   uploaded as SARIF to the GitHub Security tab.

## GitOps with Argo CD

The Argo CD Application manifest (`argocd/application.yaml`) deploys the Helm
chart automatically from this Git repository:

- Watches the `main` branch for changes.
- Deploys the Helm chart from `helm/ai-devops-incident-intelligence/`.
- Creates the `ai-devops` namespace automatically.
- Automated sync with prune and self-heal — Git is the single source of truth.

### Apply the Application

```bash
# Prerequisite: Argo CD installed and this repo registered
argocd repo add https://github.com/samkeerthana98/ai-devops-incident-intelligence.git

# Apply the Application manifest
kubectl apply -f argocd/application.yaml

# Check sync status
argocd app get ai-devops-incident-intelligence
```

See [docs/gitops.md](docs/gitops.md) for the full GitOps workflow guide.

## Project Structure

```
ai-devops-incident-intelligence/
├── app.py                  # Flask application with all endpoints
├── ollama_client.py        # Ollama HTTP API integration
├── retrieval.py            # Keyword-based runbook retrieval
├── requirements.txt        # Python dependencies
├── test_app.py             # Phase 1 tests (API endpoints)
├── test_analysis.py        # Phase 2 tests (analysis + retrieval)
├── test_dashboard.py       # Phase 3 tests (dashboard routes)
├── Dockerfile              # Production Docker image
├── .dockerignore           # Docker build exclusions
├── runbooks/               # Markdown runbooks for incident types
│   ├── http_500.md
│   ├── high_latency.md
│   └── general_troubleshooting.md
├── templates/
│   └── dashboard.html      # Jinja2 dashboard template
├── static/
│   ├── css/dashboard.css   # Responsive dashboard styles
│   └── js/dashboard.js     # Vanilla JS for dashboard interactions
├── helm/
│   └── ai-devops-incident-intelligence/
│       ├── Chart.yaml       # Helm chart metadata
│       ├── values.yaml      # Default values
│       └── templates/
│           ├── _helpers.tpl   # Template helpers
│           ├── NOTES.txt      # Post-install notes
│           ├── deployment.yaml
│           ├── service.yaml
│           └── serviceaccount.yaml
├── argocd/
│   └── application.yaml    # Argo CD Application manifest
├── docs/
│   └── gitops.md           # GitOps workflow guide
└── .github/
    └── workflows/
        └── ci.yml          # GitHub Actions CI workflow
```
