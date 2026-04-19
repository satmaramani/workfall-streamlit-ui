# Streamlit UI

Optional frontend for interacting with the multi-agent e-commerce system.

## What This Repo Does

- sends user requests to Concierge
- exposes inventory operations
- generates invoices
- fetches market intelligence
- shows workflow traces and service health
- acts as the human-facing demo layer for the backend services

## Default Port

`8501`

## Local Base URL

`http://localhost:8501`

## Depends On

- `concierge-orchestration` on `8000`
- `inventory-agent` on `8001`
- `invoice-agent` on `8002`
- `market-intelligence-agent` on `8003`

## PostgreSQL Note

The UI itself does not connect directly to PostgreSQL. However, the backend services it depends on do.

Before running the full system, make sure PostgreSQL is already running for:

- `concierge-orchestration`
- `inventory-agent`
- `invoice-agent`
- `market-intelligence-agent`

Recommended local database settings used across backend repos:

- host: `localhost`
- port: `5432`
- database: `workfall_multi_agent`
- user: `workfall`
- password: `workfall`

The backend services create their own tables automatically on startup if the configured database is reachable.

## Environment Setup

1. Copy the example file:

```powershell
copy .env.example .env
```

2. Update values if needed, especially:

- `CONCIERGE_BASE_URL`
- `INVENTORY_BASE_URL`
- `INVOICE_BASE_URL`
- `MARKET_INTELLIGENCE_BASE_URL`

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run Locally

```powershell
streamlit run app/main.py --server.port 8501
```

## Main Features

- Concierge request form with session-aware follow-up support
- Inventory catalog table, upsert form, and delete flow
- Invoice preview and generation
- Market insight lookup
- Workflow trace inspection
- Service health dashboard

## Repo Structure

```text
streamlit-ui/
  app/
  .env.example
  requirements.txt
  .gitignore
  README.md
```

## Notes

- this repo is optional for the assignment, but useful for demonstration
- it expects all backend services to be running before use
