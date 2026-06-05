# Support-Pilot ✈️

Support-Pilot is a premium, AI-powered customer support inbox management and triage workspace. It automates ticket classification, provides retrieval-augmented generation (RAG) capabilities to resolve queries using your custom knowledge base, and offers an admin dashboard for human-in-the-loop review and management.

Built with **FastAPI**, **Google Gemini 2.5 Flash**, **Pinecone**, and **SQLAlchemy**, it streamlines customer support by bridging the gap between automated AI replies and human agent review.

---

## 🌟 Key Features

1. **AI Decision Engine**: Automatically classifies incoming emails using Gemini 2.5 Flash. It identifies:
   - **Issue Category**: (e.g., *refund, billing, technical, cancellation, complaint, account, etc.*)
   - **Severity**: (*low, medium, high*)
   - **Customer Sentiment**: (*positive, neutral, negative, mixed*)
   - **Underlying Emotion**: (*frustrated, angry, concerned, happy, etc.*)
   - **Actionable Decision**: 
     - `auto_resolve`: Generates a draft using context from the Knowledge Base and automatically replies/closes the ticket.
     - `review_required`: Generates an AI draft reply but holds it in the dashboard for human review and approval.
     - `escalate`: Automatically forwards the query to the designated department email and notifies the customer.
2. **Retrieval-Augmented Generation (RAG)**: Integrates with Pinecone's serverless vector store to chunk, store, and query knowledge documents (supporting `.pdf`, `.docx`, and `.txt` files).
3. **Email Integration**: Monitors an IMAP inbox (such as Gmail) for incoming support requests, resolves threading (detecting replies via `Message-ID`, `References`, or thread IDs), and sends outbound replies or forwards via SMTP.
4. **Admin Dashboard**: A sleek, dark-themed responsive admin panel:
   - **Tickets Workspace**: Tracks open, pending, and escalated tickets. Displays conversation history, sentiment badges, and offers a draft editor where agents can modify and send AI-suggested responses.
   - **Knowledge Base Tab**: Upload documents, adjust chunk/overlap sizes, search the index directly, and manage ingested files.
   - **Email Routing Tab**: Set up and customize routing rules to map issue types to specific departments (e.g., Billing, Tech Support).
5. **Dual-Process Architecture**: A lightweight background poller checks for emails asynchronously, while the web server handles API requests and serves the dashboard.

---

## 📂 Project Structure

```text
support-pilot/
├── main.py              # Entry point for the background email listener (polls IMAP inbox)
├── server.py            # FastAPI server implementing REST API endpoints & HTML template rendering
├── config.py            # Loads and manages env configuration and similarity thresholds
├── database.py          # SQLAlchemy models (DocumentMetadata, Email, Ticket) & database connection
├── schemas.py           # Pydantic validation schemas for API requests
├── services.py          # Core helper functions for text extraction, chunking, and Pinecone vector ops
├── ai_service.py        # Gemini API client wrapper for triage analysis & draft generation
├── email_service.py     # IMAP inbox fetcher, parser, SMTP reply/forward sender, and thread resolver
├── policy.txt           # Standard customer support policy rules used in system prompt contexts
├── templates/
│   └── upload.html      # Monolithic glassmorphic frontend UI dashboard (Outfit font, CSS variables)
├── pyproject.toml       # Python dependencies configuration (managed by uv)
├── start-service.bat    # Windows batch script to launch the listener and server concurrently
└── .env                 # Environment variables configuration file (Credentials & API keys)
```

---

## 🛠️ Prerequisites

- **Python**: version `3.11` or higher is required.
- **Package Manager**: [uv](https://github.com/astral-sh/uv) is highly recommended for dependency and environment management (as used in the start scripts). Alternatively, standard `pip` can be used.

---

## 🚀 Getting Started

### 1. Clone & Set Up Environment

Create a `.env` file in the root directory and specify the following variables:

```env
EMAIL_USER = your-support-email@gmail.com
EMAIL_PASS = your-gmail-app-password
GEMINI_API_KEY = your-google-gemini-api-key
PINECONE_API_KEY = your-pinecone-api-key
PINECONE_INDEX_NAME = your-pinecone-index-name
DATABASE_URL = postgresql://username:password@hostname/database?sslmode=require
SERVER_URL = http://localhost:8000
SIMILARITY_THRESHOLD = 0.40
```

> [!IMPORTANT]
> - **Gmail Setup**: If using Gmail, you must enable **2-Step Verification** on your Google Account and generate an **App Password** for `EMAIL_PASS`. Standard passwords will be rejected by Google's SMTP/IMAP servers.
> - **Pinecone Index**: Ensure your Pinecone index supports Integrated Embeddings or is configured to match the indexing structure in `services.py`.

### 2. Install Dependencies

Install `uv`:
```bash
pip install uv
```

Then install dependencies:
```bash
uv sync
```

### 3. Running the System

You can run both processes together or launch them separately.

#### Option A: Run concurrently (Windows Batch script)
Run the convenience script:
```bash
start-service.bat
```
This script opens two separate command line windows running:
1. `uv run main.py` (Email Poller)
2. `uv run uvicorn server:app --reload` (FastAPI Server)

#### Option B: Launch manually
**Start the FastAPI server:**
```bash
uv run uvicorn server:app --reload --port 8000
```

**Start the background email listener:**
```bash
uv run main.py
```

Open your browser and navigate to `http://localhost:8000` to access the Admin Dashboard.

---

## 📊 Database Schema Details

The system uses SQLAlchemy to manage three tables:
- **`tickets`**: Stores the logical thread groupings (`ticket_id`), customer contact details, subject, body, and the full history of messages. It also records triage results (`severity`, `sentiment`, `emotion`, `issue`) and AI metadata like `ai_decision`, `ai_draft_reply`, and `forwarded_to`.
- **`emails`**: Contains the department rules configuration used to map issues to specialists.
- **`document_metadata`**: Tracks chunk IDs, filenames, and Pinecone vector IDs to coordinate knowledge document deletion and references.

---

## ⚙️ AI Classification & Triage Flow

When an email lands in the inbox:
1. **Fetch & Clean**: The poller extracts the plaintext body, sender address, and thread headers.
2. **Context Retrieval**: The email content is queried against the Pinecone index to retrieve up to 5 matching chunks from the ingested documents above the `SIMILARITY_THRESHOLD`.
3. **Triage Analysis**: Gemini is prompted with the incoming email, knowledge base context, and department rules to output a structured JSON response.
4. **Action Execution**:
   - **`auto_resolve`**: A reply is dispatched immediately using SMTP in-thread reference headers, and the ticket status is saved as `Closed`.
   - **`escalate`**: The ticket is forwarded to the matching department email (e.g., billing inquiries go to Billing), a notice is sent to the customer, and the ticket is set to `Escalated`.
   - **`review_required`**: No email is sent. The generated reply draft and reasoning are stored. The ticket is marked `Pending` and highlights itself in the Admin Dashboard for review.

---

## 🎨 UI Dashboard Showcase

The dashboard features:
- **Real-time Stat Cards**: Total Open, Pending Review, Escalated, High Severity, and Closed metrics.
- **Active Thread Viewer**: Allows agents to inspect the exact chat layout of email exchanges (with distinct visual styles for inbound vs outbound messages).
- **Interactive Draft Console**: Agents can review AI-drafted replies, modify them directly in a textarea, and hit **Approve & Send** to transmit the email instantly via SMTP.
- **Document Management**: Drag-and-drop file uploader with configurable chunk settings, coupled with an active document list highlighting source files.
- **Department Routing**: Intuitive table listing current rules, complete with a creation form to add or edit existing departments.
