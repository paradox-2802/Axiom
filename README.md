# Axiom

Axiom is a user-centric document intelligence platform built with React and FastAPI. Each chat session is permanently linked to exactly one uploaded PDF, with isolated vector search and streaming LLM responses.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Python 3.12 |
| Database | MongoDB (Motor) |
| Vector store | Qdrant (one collection per chat session) |
| Queue | Arq + Valkey/Redis |
| Embeddings & LLM | Hugging Face Inference API |
| PDF processing | pdfplumber + LangChain text splitters |

## Project structure

```
Axiom/
├── backend/         # FastAPI API + Arq worker
├── frontend/        # React frontend
└── docker-compose.yml
```

### Backend (`backend/`)

- `main.py` — FastAPI application entry point
- `core/` — Config, database, security, AI clients
- `routers/` — HTTP route handlers
- `services/` — RAG, ingestion, chat helpers
- `models/` — Pydantic request/response schemas
- `middleware/` — Auth dependencies
- `worker/` — Arq background worker
- `scripts/` — Database migration utilities
- `utils/` — File upload and SSE helpers

### Frontend (`frontend/`)

- `src/pages/` — Route-level views
- `src/components/` — Reusable UI
- `src/utils/` — API, auth, streaming

## Quick start

### Prerequisites

- Docker (recommended), or Node.js 20+ and Python 3.12+
- Hugging Face API key
- MongoDB connection string

### Environment

Create `backend/.env` and `frontend/.env` locally (both are gitignored). Required backend variables: `MONGODB_URI`, `JWT_SECRET`, `HUGGINGFACE_API_KEY`, `QDRANT_URL`, `REDIS_HOST`, `REDIS_PORT`, `PORT`. Optional: `JWT_REFRESH_SECRET` (defaults to `JWT_SECRET`), `CORS_ORIGINS` (comma-separated frontend URLs; defaults to `http://localhost:5173`), `QDRANT_COLLECTION` (legacy shared collection name for pre-migration chats; defaults to `axiom-documents`). For local frontend dev, set `VITE_API_BASE=http://localhost:8000` in `frontend/.env` (Docker Compose sets this automatically).

Docker Compose overrides `REDIS_HOST` and `QDRANT_URL` for in-network service names; use `localhost` in `.env` for both Docker and local `uvicorn`/`arq`.

### Docker

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Qdrant | http://localhost:6333 |

### Local development

```bash
# Terminal 1 — API
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Worker
cd backend
arq worker.worker.WorkerSettings

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Integration tests use an in-memory MongoDB mock (`mongomock-motor`) and do not require Redis, Qdrant, or Hugging Face to be running. Rate limiting is disabled in tests by default.

Optional rate limit env vars: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_STORAGE` (`redis` or `memory`), `RATE_LIMIT_AUTH`, `RATE_LIMIT_UPLOAD`, `RATE_LIMIT_CHAT`, `REDIS_RATE_LIMIT_DB`.

### Legacy data migration

Run once to add document fields to existing chat sessions (safe to re-run):

```bash
cd backend
python scripts/migrate_chats.py
```

Existing users and chat history are preserved. Legacy chats with message history continue to retrieve from the shared `axiom-documents` collection until users create new session-scoped chats.

## API overview

### Auth
- `POST /auth/signup` — Register (returns access + refresh tokens)
- `POST /auth/login` — Login (returns access + refresh tokens)
- `POST /auth/refresh` — Exchange refresh token for new access + refresh tokens

### Chat (JWT required)
- `POST /chat/create` — Create session
- `GET /chat/list` — List sessions
- `GET /chat/history/:chatId` — Get messages and document status
- `POST /chat` — Send message (SSE stream; requires completed ingestion)
- `DELETE /chat/:chatId` — Delete session and all associated resources

### Upload (JWT required)
- `POST /upload` — Upload PDF to a chat session (`chatId` form field + `pdf` file). Returns `409` if the session already has a document.

## Session lifecycle

```
NEW → PDF Uploaded → Processing → Ready → Chat Enabled
```

Each chat session accepts exactly one PDF. After upload, `document_locked` is set and the document cannot be replaced. Create a new chat to analyse another PDF.

Vector collections are named `axiom_<chatId>` and are deleted when the chat is deleted.

## Features

- User authentication (JWT access + refresh tokens)
- One document per chat session
- Session-scoped vector search
- Chat sessions with conversation history
- Streaming assistant responses (SSE)
- Source citation from retrieved chunks
- Automatic token refresh on the frontend
