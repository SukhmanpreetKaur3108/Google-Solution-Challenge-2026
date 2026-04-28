# PoF-AI — Proof-of-Fairness AI

> **Google Solution Challenge 2026** | Team project on *Unbiased AI Decision: Ensuring Fairness and Detecting Bias in Automated Decisions*

---

## What Is PoF-AI?

Computer programs now make life-changing decisions — who gets a job, a bank loan, or medical care. When these programs learn from flawed historical data, they amplify discrimination. **PoF-AI doesn't just detect bias — it proves every decision is fair in real-time with a cryptographically signed, legally auditable Fairness Certificate.**

Think of it like **SSL certificates for websites, but for AI decisions.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      pof-ai-dashboard (React)                   │
│   Landing · Demo · Certificate Viewer · Explorer · Dashboard    │
└────────────────────────┬────────────────────────────────────────┘
                         │  REST API (API Gateway)
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼──────────┐         ┌──────────▼─────────┐
│  pof-ai-backend   │         │   pof-ai-log        │
│  (FastAPI/Cloud   │         │  (Merkle Audit Log  │
│   Run)            │         │   FastAPI/Cloud Run)│
└────────┬──────────┘         └──────────┬──────────┘
         │                               │
    ┌────┴──────────────────────────┐    │
    │    Five Fairness Engines      │    │
    │  ┌─────────────────────────┐ │    │
    │  │ 1. Statistical (Fairlearn│ │    │
    │  │ 2. Intersectional Surface│ │    │
    │  │ 3. Causal (DoWhy)       │ │    │
    │  │ 4. Adversarial (Gemini) │ │    │
    │  │ 5. Regulatory (YAML KB) │ │    │
    │  └─────────────────────────┘ │    │
    └───────────────────────────────┘    │
         │                               │
    ┌────┴──────┐  ┌────────────┐  ┌────┴───────┐
    │ Vertex AI │  │  Firestore │  │   Cloud    │
    │  (Model)  │  │            │  │  Storage   │
    └───────────┘  └────────────┘  └────────────┘
         │
    ┌────┴──────┐
    │ Cloud KMS │  (Ed25519 certificate signing)
    └───────────┘
```

---

## Prerequisites

Install these **before** anything else:

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| npm | 9+ | bundled with Node |
| Google Cloud SDK | latest | `gcloud` CLI |
| Terraform | 1.7+ | https://terraform.io |
| Docker | 24+ | https://docker.com |
| LibreOffice | any | for notebook PDF export (optional) |

Python packages (global):

```bash
pip install uv          # fast package manager
pip install markitdown  # for PPT/doc reading (optional)
```

Google Cloud APIs to enable:

```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  cloudkms.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  apigateway.googleapis.com \
  bigquery.googleapis.com
```

---

## Setup Guide (Step-by-Step)

### Step 1 — Clone & configure environment

```bash
git clone https://github.com/YOUR_ORG/pof-ai.git
cd pof-ai
cp pof-ai-backend/.env.example pof-ai-backend/.env
# Edit .env — fill in your GCP project ID, Vertex endpoint, KMS key names, etc.
```

### Step 2 — Backend: install dependencies

```bash
cd pof-ai-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Backend: run locally

```bash
uvicorn app.main:app --reload --port 8080
# API docs: http://localhost:8080/docs
```

### Step 4 — Train the bias-injected model

```bash
cd model_training
pip install -r requirements.txt
python train_hiring_model.py
# This generates data, trains LogReg + XGBoost, evaluates with Fairlearn,
# and uploads the XGBoost model to Vertex AI Model Registry.
```

### Step 5 — Run the Jupyter notebook (demo evidence)

```bash
cd notebooks
jupyter lab 01_dataset_and_bias.ipynb
# Walk through dataset creation and bias measurements with plots.
```

### Step 6 — Frontend: install & run

```bash
cd pof-ai-dashboard
npm install
npm run dev
# Open http://localhost:5173
```

### Step 7 — Audit log microservice

```bash
cd pof-ai-log
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```

### Step 8 — Run the end-to-end demo

```bash
cd demo
pip install -r requirements.txt   # if not already installed
python run_demo.py
# Loads 3 pre-baked applicants, posts to /score, prints comparison table,
# opens dashboard URLs in browser.
```

---

## Cloud Deployment (Google Cloud)

### One-time infrastructure setup

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
# Provisions Cloud Run, Vertex AI Endpoint, Firestore, GCS, KMS, etc.
```

### Deploy backend to Cloud Run

```bash
cd pof-ai-backend
gcloud builds submit --config cloudbuild.yaml
```

### Deploy frontend to Firebase Hosting

```bash
cd pof-ai-dashboard
npm run build
firebase deploy --only hosting
```

### CI/CD (GitHub Actions)

Push to `main` automatically:
1. Runs `pytest` for all backend tests
2. Builds Docker images via Cloud Build
3. Pushes to Artifact Registry
4. Applies Terraform
5. Deploys frontend to Firebase Hosting

---

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/score` | Submit hiring decision → get Fairness Certificate |
| `GET` | `/cert/{id}` | Retrieve a certificate |
| `GET` | `/health` | Health check |

**Audit Log Service:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/append` | Append certificate to Merkle log |
| `GET` | `/entry/{idx}` | Get leaf + inclusion proof |
| `GET` | `/sth` | Latest signed tree head |
| `GET` | `/verify/{cert_id}` | Inclusion proof for a certificate |

---

## Project Structure

```
pof-ai/
├── README.md
├── pof-ai-backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, /score endpoint
│   │   ├── orchestrator.py          # FairnessOrchestrator (asyncio.gather)
│   │   ├── engines/
│   │   │   ├── statistical.py       # Fairlearn metrics engine
│   │   │   ├── intersectional.py    # Intersectional surface engine
│   │   │   ├── causal.py            # DoWhy causal counterfactual engine
│   │   │   ├── adversarial.py       # Gemini-powered red-team engine
│   │   │   ├── regulatory.py        # Regulatory compliance engine
│   │   │   └── regulations.yaml     # EU AI Act, GDPR, NIST, DPDP KB
│   │   ├── cert/
│   │   │   └── certificate.py       # Signed JSON-LD FairnessCertificate
│   │   ├── clients/
│   │   │   ├── vertex.py            # Vertex AI prediction client
│   │   │   ├── firestore.py         # Firestore write/read
│   │   │   ├── bigquery.py          # Historical decisions query
│   │   │   └── gemini.py            # Gemini API wrapper
│   │   └── models/
│   │       └── schemas.py           # Pydantic v2 request/response models
│   ├── tests/
│   ├── Dockerfile
│   ├── cloudbuild.yaml
│   ├── requirements.txt
│   └── .env.example
├── pof-ai-log/
│   ├── app/
│   │   ├── main.py                  # Merkle audit log service
│   │   └── merkle.py                # RFC 6962-style Merkle tree
│   └── tests/
├── pof-ai-dashboard/
│   ├── src/
│   │   ├── pages/                   # Landing, Demo, CertViewer, Explorer, Dashboard
│   │   ├── components/              # Reusable UI components
│   │   └── hooks/                   # TanStack Query hooks
│   ├── package.json
│   ├── vite.config.ts
│   └── firebase.json
├── model_training/
│   ├── train_hiring_model.py        # Bias-injected dataset + model training
│   ├── model_card.md
│   └── requirements.txt
├── notebooks/
│   └── 01_dataset_and_bias.ipynb   # Bias measurement demo evidence
├── demo/
│   └── run_demo.py                  # End-to-end demo orchestrator
└── infra/
    ├── main.tf                      # Terraform: Cloud Run, Vertex, Firestore, KMS...
    ├── variables.tf
    ├── outputs.tf
    └── cost_estimate.md
```

---

## The Five Fairness Engines

| Engine | Library | What It Checks |
|--------|---------|----------------|
| **Statistical** | Fairlearn | Demographic parity, equalized odds, disparate impact |
| **Intersectional** | Custom | Bias at subgroup intersections (e.g., Black woman aged 25–34) |
| **Causal** | DoWhy | Counterfactual fairness — would outcome change if only protected attribute changed? |
| **Adversarial** | Gemini 1.5 Pro | Near-twin probe generation and flip-rate measurement |
| **Regulatory** | YAML KB | EU AI Act, GDPR Art 22, NIST AI RMF, India DPDP Act 2023 |

---

## Fairness Certificate (JSON-LD)

Every decision produces a cryptographically signed certificate:

```json
{
  "@context": "https://pof-ai.app/context/v1",
  "@type": "FairnessCertificate",
  "certificate_id": "01932abc-...",
  "issued_at": "2026-04-25T10:30:00Z",
  "statistical_score": 0.91,
  "adversarial_flip_rate": 0.05,
  "regulatory_compliance_percent": 91.7,
  "signature": "Ed25519:base64...",
  "previous_certificate_hash": "sha256:abc123..."
}
```

Scan the QR code on any certificate to verify it in your browser — no server trust required.

---

## Team

Names: Sukhmanpreet Kaur, Aasmeet Kaur 

---

## License

MIT License — see [LICENSE](LICENSE)

---

## References

- Mitchell et al. (2019) — Model Cards for Model Reporting
- Chiappa (2019) — Path-specific Counterfactual Fairness
- Haber & Stornetta (1991) — How to time-stamp a digital document
- RFC 6962 — Certificate Transparency
- EU AI Act (2024), GDPR Art 22, NIST AI RMF 1.0, India DPDP Act 2023
