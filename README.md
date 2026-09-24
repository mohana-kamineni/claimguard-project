# ClaimGuard

This is a microservice-based expense reimbursement application. It allows employees to submit expense claims through a web interface or REST API. Each claim is evaluated by a separate, dedicated Policy service before being stored in a persistent PostgreSQL database.

## Architecture

The system consists of two application microservices and one database service:

```text
                  +-----------------------------------+
                  |            Web Browser            |
                  +-----------------+-----------------+
                                    |
                    HTTP / Port 8000 (NodePort 30080)
                                    v
+-----------------------------------+-----------------------------------+
|                          Expense Service                              |
|  - Serves web dashboard (HTML/Jinja2) and REST API (/api/claims)      |
|  - Validates claim input (amounts, categories, currency)              |
|  - Calls Policy Service synchronously before inserting records        |
+-------------------+-------------------------------+-------------------+
                    |                               |
    SQL (psycopg / port 5432)        HTTP POST /api/evaluate (port 8000)
                    v                               v
+-------------------+---------------+   +-----------+-------------------+
|        PostgreSQL Database        |   |        Policy Service         |
|  - Persistent storage (PVC / RWO) |   |  - Stateless rules engine     |
|  - Stores claims table            |   |  - Evaluates spending limits  |
+-----------------------------------+   +-------------------------------+
```

* **Expense Service:** Provides the public-facing HTTP interface (both a Jinja2 web form and JSON REST endpoints). When an expense is submitted, Expense validates the payload and calls the Policy Service over HTTP. It only persists the claim to PostgreSQL if the Policy Service returns a valid decision (`allowed` or `denied`), saving a snapshot of the decision and reason codes.
* **Policy Service:** A stateless rules engine that evaluates claim amount, category, and currency against configurable spending thresholds. It does not connect to the database.
* **PostgreSQL:** Stores the submitted claims. Runs as a dedicated container with a persistent volume to preserve data across container restarts.

## Technologies

* **Backend:** Python 3.12, FastAPI, Uvicorn
* **Frontend:** Jinja2 templates, HTML5, CSS
* **Database & ORM:** PostgreSQL 16, SQLAlchemy 2.0, Psycopg 3
* **HTTP Client:** HTTPX (synchronous)
* **Testing:** Pytest
* **Containers & Orchestration:** Docker, Docker Compose, Kubernetes

## Project Structure

```text
claimguard/
├── docker-compose.yml          # Local PostgreSQL container for development
├── .env.example                # Example environment variables for local runs
├── k8s/                        # Kubernetes manifests
│   ├── configmap.yaml          # Shared configuration and policy thresholds
│   ├── secret.yaml.example     # Database credentials template
│   ├── postgres-pvc.yaml       # PersistentVolumeClaim for database
│   ├── postgres-deployment.yaml# PostgreSQL Deployment (1 replica)
│   ├── postgres-service.yaml   # PostgreSQL ClusterIP Service
│   ├── policy-deployment.yaml  # Policy Service Deployment
│   ├── policy-service.yaml     # Policy Service ClusterIP Service
│   ├── expense-deployment.yaml # Expense Service Deployment
│   └── expense-service.yaml    # Expense Service NodePort Service
└── services/
    ├── expense/                # Expense service application and tests
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── app/                # FastAPI app, database models, templates
    │   └── tests/              # Unit and integration test suite
    └── policy/                 # Policy service application and tests
        ├── Dockerfile
        ├── requirements.txt
        ├── app/                # Rules engine and evaluation endpoints
        └── tests/              # Unit tests for policy rules
```

## Running Locally
To run ClaimGuard directly on your host machine using Python virtual environments:

### Prerequisites

- Python 3.12+
- Docker Desktop installed and running.

### 1. Start the PostgreSQL database
From the repository root:
```bash
docker compose up -d db
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```

### 3. Run the Policy Service
In a new terminal:
```bash
cd services/policy
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 4. Run the Expense Service
In another terminal:
```bash
cd services/expense
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser to access the application dashboard.

## Running with Docker

You can build and run both microservices as standalone Docker containers:

### Build Images
```bash
# Build Expense service
docker build -t claimguard-expense:latest ./services/expense

# Build Policy service
docker build -t claimguard-policy:latest ./services/policy
```

Published images are also available on Docker Hub:
* `mohanakamineni/claimguard-expense:v1.0.0`
* `mohanakamineni/claimguard-policy:v1.0.0`

## Deploying to Kubernetes

The application is configured for deployment on Kubernetes (e.g., Docker Desktop Kubernetes, Minikube, or Kind).

### 1. Prerequisites
Ensure your Kubernetes cluster is running and `kubectl` is configured:
```bash
kubectl cluster-info
```

### 2. Create the Secret
Create `k8s/secret.yaml` from the example template:
```bash
cp k8s/secret.yaml.example k8s/secret.yaml
kubectl apply -f k8s/secret.yaml
```

### 3. Deploy the Stack
Deploy the configuration, database, and microservices:
```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Deploy PostgreSQL (PVC, Deployment, Service)
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml

# Deploy Policy Service
kubectl apply -f k8s/policy-deployment.yaml
kubectl apply -f k8s/policy-service.yaml

# Deploy Expense Service
kubectl apply -f k8s/expense-deployment.yaml
kubectl apply -f k8s/expense-service.yaml
```

### 4. Verify Deployments
Check that all pods reach the `Running` state:
```bash
kubectl get pods -w
```

### 5. Access the Application
The Expense service is exposed via NodePort on port `30080`.

* **Direct NodePort:** `http://<node-ip>:30080/`
* **Port Forwarding (convenient for local clusters):**
  ```bash
  kubectl port-forward svc/expense 8000:8000
  ```
  Then open `http://localhost:8000` in your web browser.

## Testing

Each microservice includes automated pytest test suites covering health checks, input validation, rules evaluation, and database persistence.

### Run Expense Tests
```bash
# Requires local PostgreSQL running (docker compose up -d db)
cd services/expense
pytest
```

### Run Policy Tests
```bash
cd services/policy
pytest
```

## Notes

* **Authentication:** There is no user authentication or login system implemented. Any `employee_id` can be entered in the form; this is an accepted simplification for this course project.
* **Database Scaling:** PostgreSQL runs as a single replica backed by a `ReadWriteOnce` persistent volume claim. It is not horizontally scaled.
* **Concurrent Startup:** Expense uses a PostgreSQL transaction-scoped advisory lock (`pg_advisory_xact_lock`) during startup to serialize table creation safely if multiple replicas launch at the same time.
* **Service Networking:** Inside the Kubernetes cluster, Expense discovers the Policy service via internal cluster DNS (`http://policy:8000`), and PostgreSQL via `postgres:5432`.
