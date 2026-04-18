# Streamlit UI

Optional user interface for interacting with the multi-agent e-commerce system.

## Responsibilities

- provide a chat-style entrypoint to the Concierge service
- expose forms for inventory, invoice, and market insight workflows
- display service health and workflow traces
- act as a thin client, not a replacement for backend business logic

## Default Port

`8501`

## Local Run Target

`http://localhost:8501`

## Planned Dependencies

- Streamlit
- httpx
- optional plotting and observability viewers later

## Run Locally

```bash
streamlit run app/main.py --server.port 8501
```

The UI expects the Concierge service on port `8000` and the three backend agent services on ports `8001` to `8003`.

## Repo Layout

```text
streamlit-ui/
  app/
  tests/
  .env.example
  requirements.txt
  .gitignore
  README.md
```
