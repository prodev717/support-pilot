# Support-Pilot

Support-Pilot is an AI-powered customer support inbox management and triage workspace. It automates ticket classification using Google Gemini, resolves queries via a custom Retrieval-Augmented Generation (RAG) knowledge base, and provides a modern React admin dashboard for human-in-the-loop review and management.

Built with **FastAPI**, **React(Vite) + TailwindCSS**, **Google Gemini 2.5 Flash**, **Pinecone**, and **SQLAlchemy (PostgreSQL)**.

---

## Key Features

### AI Decision Engine
Every incoming email is automatically triaged by Gemini 2.5 Flash, which classifies:
- **Issue Category**: `question`, `request`, `complaint`, `refund`, `billing`, `technical`, `account`, `delivery`, `return`, `escalation`, `other`, etc.
- **Severity**: `low`, `medium`, `high`
- **Customer Sentiment**: `positive`, `neutral`, `negative`, `mixed`
- **Underlying Emotion**: `neutral`, `happy`, `satisfied`, `confused`, `concerned`, `frustrated`, `angry`, `urgent`, `disappointed`, `grateful`, `sad`
- **Actionable Decision**:
  - `auto_resolve` — Automatically replies and closes the ticket using knowledge base context.
  - `review_required` — Saves an AI-generated draft to the dashboard for human review before sending.
  - `escalate` — Forwards the ticket to a department email and notifies the customer.

### RAG Knowledge Base
Integrates with Pinecone's serverless vector store to chunk, embed, and query uploaded documents. Supports `.pdf`, `.docx`, and `.txt` files with configurable chunk size and overlap.

### Email Integration (Gmail / IMAP)
- Monitors a Gmail inbox (IMAP) for new support emails every 60 seconds.
- Extracts `X-GM-THRID` via IMAP metadata for accurate Gmail thread detection.
- Resolves email threads using subject tags (`[Ticket #N]`), Gmail thread IDs, and `Message-ID`/`References` headers — in that priority order.
- Sends replies in-thread via SMTP, preserving email client threading headers.

### React Admin Dashboard
A responsive SPA (served at `http://localhost:5173`) with four views:
- **Home** — Analytics overview: ticket counts by status, document count, email routing stats, and system health check for all services.
- **Tickets Workspace** — View, filter, and manage tickets. Inspect full conversation threads with customer and AI reply messages visually separated. Edit and send AI draft replies directly from the dashboard. Supports creating and deleting tickets manually.
- **Knowledge Base** — Upload documents (PDF/DOCX/TXT), configure chunking parameters, perform semantic search, and delete documents.
- **Email Routing** — Configure department routing rules (department name, email address, and description) used by the AI escalation engine.

### Cached & Synced UI
The dashboard uses **SWR** (Stale-While-Revalidate) for smart data fetching:
- Data is displayed instantly from cache when navigating between pages.
- Background sync keeps data fresh automatically.
- Every page has a **Refresh button** with a live syncing indicator.
- API calls are deduplicated to prevent unnecessary requests.

### System Health Monitoring
`GET /health` reports the status of all four backend services:
- PostgreSQL database
- Pinecone vector index
- Google Gemini API
- Gmail IMAP/SMTP connection

---

## Project Structure

```text
support-pilot/
├── main.py              # Email poller entry point — polls inbox every 60s
├── server.py            # FastAPI server with all REST API endpoints
├── config.py            # Environment variable loader (credentials, thresholds)
├── database.py          # SQLAlchemy models: DocumentMetadata, Email, Ticket
├── schemas.py           # Pydantic validation schemas for API request bodies
├── services.py          # Text extraction, chunking, and Pinecone vector operations
├── ai_service.py        # Google Gemini client: triage analysis & draft generation
├── email_service.py     # IMAP inbox reader, thread resolver, SMTP sender
├── policy.txt           # Support policy fed into AI system prompts
├── pyproject.toml       # Python project config & dependencies (managed by uv)
├── start-service.bat    # Windows launcher: starts all 3 processes concurrently
├── .env                 # Environment variables (credentials, API keys)
└── frontend/            # React + Vite admin dashboard
    ├── src/
    │   ├── App.jsx              # Root router (React Router v7)
    │   ├── main.jsx             # Vite entry point
    │   ├── Sidebar.jsx          # Collapsible navigation sidebar
    │   ├── PageHeader.jsx       # Top header with branding
    │   ├── Home.jsx             # Analytics dashboard page
    │   ├── TicketsWorkspace.jsx # Tickets management page
    │   ├── KnowledgeBase.jsx    # Document management page
    │   ├── EmailRouting.jsx     # Department routing config page
    │   └── useCache.js          # Shared SWR data-fetching hook
    ├── package.json
    └── vite.config.js
```

---

## Database Schema

Three PostgreSQL tables managed by SQLAlchemy (auto-created on server startup via `Base.metadata.create_all`):

### `tickets`
| Column | Type | Description |
|---|---|---|
| `id` | Integer PK | Row ID |
| `ticket_id` | Integer (indexed) | Logical thread ID — multiple rows share this for multi-message threads |
| `customer_email` | String | Sender's email address |
| `subject` | String | Email subject |
| `body` | Text | Plaintext email body |
| `message_id` | String (unique) | RFC 2822 `Message-ID` header |
| `thread_id` | String | Gmail `X-GM-THRID` or `Thread-Index` value |
| `issue` | String | Classified issue category |
| `severity` | String | `low` / `medium` / `high` |
| `sentiment` | String | `positive` / `neutral` / `negative` / `mixed` |
| `emotion` | String | Detected customer emotion |
| `ticket_status` | String | `Open` / `Pending` / `Escalated` / `Closed` |
| `ai_decision` | String | Decision + explanation from triage |
| `ai_draft_reply` | Text | AI-generated reply draft |
| `draft_sent` | Boolean | `true` if the draft has been sent to the customer |
| `forwarded_to` | String | Department email if escalated |
| `created_at` | Timestamp | Row creation time |
| `updated_at` | Timestamp | Auto-updated on any change |

### `emails`
Department routing rules used by the AI triage engine for escalation decisions.

### `document_metadata`
Tracks Pinecone vector IDs per document chunk, enabling targeted deletion.

> [!IMPORTANT]
> SQLAlchemy's `create_all` only creates new tables — it does **not** apply changes to existing tables.
> If you modify the schema (e.g., add a column), you must run a manual `ALTER TABLE` SQL command or set up Alembic for migrations.

---

## Prerequisites

- **Python** `3.11+`
- **Node.js** `18+` with npm
- **uv** — fast Python package manager ([install guide](https://github.com/astral-sh/uv))
- A **PostgreSQL** database (We recommend using NeonDB)
- A **Google Gemini API key** (with access to `gemini-2.5-flash`)
- A **Pinecone** account with a serverless index that supports integrated embeddings
- A **Gmail account** with IMAP enabled and an **App Password** generated (requires 2-Step Verification)

---

## Getting Started

### 1. Configure Environment Variables

Copy the `.env.example` files to `.env` in both the root and `frontend/` directories:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Update the variables in the `.env` files:

```env
EMAIL_USER=your-support-email@gmail.com
EMAIL_PASS=your-gmail-app-password
GEMINI_API_KEY=your-google-gemini-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=your-pinecone-index-name
DATABASE_URL=postgresql://username:password@hostname/database?sslmode=require
SERVER_URL=http://localhost:8000
SIMILARITY_THRESHOLD=0.40
```

> [!NOTE]
> `SIMILARITY_THRESHOLD` controls the minimum vector similarity score (0–1) for a knowledge base chunk to be included in the AI context. `0.40` is a good default.

> [!IMPORTANT]
> **Gmail Setup**: Enable **2-Step Verification** on your Google account and generate an [App Password](https://myaccount.google.com/apppasswords) for `EMAIL_PASS`. Standard Gmail passwords are rejected by IMAP/SMTP.

### 2. Install Dependencies

**Backend:**
```bash
pip install uv
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
```

### 3. Run the System

#### Option A — Windows (all-in-one)
Run the convenience batch script to start all three processes in separate terminal windows:
```bat
start-service.bat
```
This launches:
1. `uv run main.py` — Email poller (checks inbox every 60 seconds)
2. `uv run uvicorn server:app --reload` — FastAPI backend on `http://localhost:8000`
3. `cd frontend && npm run dev` — React dashboard on `http://localhost:5173`

#### Option B — Manual

**Backend API server:**
```bash
uv run uvicorn server:app --reload --port 8000
```

**Email poller:**
```bash
uv run main.py
```

**Frontend dev server:**
```bash
cd frontend
npm run dev
```

Open **`http://localhost:5173`** in your browser to access the admin dashboard.

---

## AI Triage Flow

When a new email arrives in the inbox:

1. **Fetch & Parse** — IMAP fetches the email, extracting the sender, subject, body, `Message-ID`, `References`, and `X-GM-THRID` (Gmail thread ID from IMAP metadata).
2. **Thread Resolution** — The system resolves which ticket thread this email belongs to by checking (in priority order):
   - Subject tag `[Ticket #N]`
   - Matching `thread_id` in the database
   - Matching `message_id` / `References` chain
   - If no match, a new `ticket_id` is assigned.
3. **Knowledge Base Lookup** — The email body is queried against Pinecone. Up to 5 chunks above the `SIMILARITY_THRESHOLD` are retrieved as context.
4. **AI Analysis** — Gemini is prompted with the email, retrieved KB context, and available department routing rules. It returns a structured JSON response with issue, severity, sentiment, emotion, decision, explanation, and a draft reply.
5. **Action Execution**:
   - **`auto_resolve`** → SMTP reply sent in-thread, ticket saved as `Closed`, `draft_sent = true`.
   - **`review_required`** → Draft saved to DB, ticket marked `Pending`. Agent reviews and sends from the dashboard.
   - **`escalate`** → Email forwarded to the department; customer notified; ticket marked `Escalated`.
6. **Persistence** — A new row is added to the `tickets` table for every inbound message.

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tickets` | List all tickets (latest row per thread). Supports `?status=` filter. |
| `GET` | `/tickets/{ticket_id}` | Get full ticket detail with all conversation messages (user + AI). |
| `POST` | `/tickets` | Create a ticket manually. |
| `PUT` | `/tickets/{ticket_id}` | Update status, severity, routing on a ticket. |
| `DELETE` | `/tickets/{ticket_id}` | Delete all rows in a ticket thread. |
| `POST` | `/tickets/{ticket_id}/send-draft` | Send the (optionally edited) AI draft reply and close the ticket. |
| `GET` | `/emails` | List department routing rules. |
| `POST` | `/emails` | Create a routing rule. |
| `PUT` | `/emails/{email_id}` | Update a routing rule. |
| `DELETE` | `/emails/{email_id}` | Delete a routing rule. |
| `POST` | `/upload` | Upload a document (PDF/DOCX/TXT) to the knowledge base. |
| `GET` | `/documents` | List all ingested documents. |
| `GET` | `/search` | Semantic search the knowledge base. Params: `query`, `top_k`. |
| `DELETE` | `/documents/{document_id}` | Remove a document and its Pinecone vectors. |
| `GET` | `/health` | System health check for all 5 services. |
| `GET` | `/poll-check` | Liveness endpoint polled by `main.py`. |

---

## Dashboard Pages

| Page | Route | Description |
|---|---|---|
| Home | `/` | Analytics cards (ticket counts, document count, routing rules) + service health status |
| Tickets Workspace | `/tickets` | Filter, view, and manage tickets. Conversation thread with user/AI message bubbles. Draft editor for pending tickets. |
| Knowledge Base | `/knowledge-base` | Upload documents, configure chunk size/overlap, semantic search, delete documents. |
| Email Routing | `/email-routing` | Create/edit/delete department routing rules used for escalation. |
