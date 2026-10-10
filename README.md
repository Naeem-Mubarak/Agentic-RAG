# Agentic RAG

A document-aware, tool-using assistant that combines **agentic routing**, **hybrid retrieval**, and **retrieval-augmented generation (RAG)**. Ask questions about indexed PDFs, discover and load documents from a local folder, search the web when local context is insufficient, and inspect or manage documents stored in PostgreSQL—all through a chat interface.

![Agentic RAG Architecture](assets/architecture.png)

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [How Retrieval Works](#how-retrieval-works)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [API Overview](#api-overview)
- [Security Notes](#security-notes)
- [Limitations and Future Improvements](#limitations-and-future-improvements)

## Overview

This project uses an agent workflow to decide how to handle a user's request rather than sending every query through a single retrieval chain. A query is classified and routed to the appropriate path: document discovery/loading, database operations, a general response, or RAG.

For document questions, the system retrieves candidate passages using both vector similarity and PostgreSQL full-text search, combines the ranked results with Reciprocal Rank Fusion (RRF), evaluates the retrieved context, and can invoke web search when additional evidence is needed. The final response path depends on the relevance and ambiguity of the available context.

## Key Features

- **Agentic query routing:** classifies requests and routes them to document, database, retrieval, or general-response workflows.
- **PDF discovery and ingestion:** explores a configured local folder, filters PDF files, loads selected documents, and prepares them for indexing.
- **Hybrid retrieval:** combines dense vector search with PostgreSQL full-text keyword search.
- **Reciprocal Rank Fusion:** merges ranked retrieval results into a single candidate list.
- **Context refinement:** evaluates retrieved documents and refines evidence before answer generation.
- **Web search fallback:** uses Tavily through a Model Context Protocol (MCP) tool when web evidence is needed.
- **MCP tool servers:** separates filesystem, web-search, and database operations into dedicated tool servers.
- **Persistent chat history:** stores chat sessions and conversation turns in PostgreSQL.
- **Streaming responses:** streams generated answers and exposes workflow progress to the frontend.
- **Browser-based interface:** includes chat history, a folder browser, settings, and PDF upload controls.

## Architecture

At a high level, the application consists of a frontend, a FastAPI service, a LangGraph agent, an ingestion/retrieval subsystem, MCP tool servers, and PostgreSQL.

### Query workflow

1. The frontend sends a message to the FastAPI backend.
2. The intent-classification node interprets the request and rewrites it where appropriate, using conversation history.
3. The router chooses a path:
   - **Document actions:** validate the configured folder and use filesystem tools to discover or select PDFs.
   - **Database actions:** use database tools to inspect or manage indexed documents.
   - **General questions:** generate a response without document retrieval.
   - **Knowledge questions:** retrieve relevant passages from the vector store and keyword index.
4. The retrieval evaluator and document-classification/refinement nodes determine whether the available evidence is relevant, insufficient, or ambiguous.
5. When appropriate, the workflow invokes web search and incorporates the returned source material.
6. A response-generation node produces the answer, which is streamed to the client and saved in chat history.

### Document ingestion workflow

1. Discover and select PDFs from the configured local directory.
2. Load PDF pages and their metadata using PyMuPDF-based document loading.
3. Split the page documents into chunks using a recursive character splitter (500-character chunks with 20-character overlap).
4. Generate embeddings in batches.
5. Store chunk text, embeddings, metadata, page numbers, and document names in PostgreSQL.
6. Create indexes for vector similarity and keyword retrieval.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python (project metadata requires Python 3.14 or newer) |
| API | FastAPI, Uvicorn |
| Agent orchestration | LangGraph |
| LLM and prompt integration | LangChain |
| LLM providers | Groq-hosted model and Google Gemini |
| Embeddings | Hugging Face Inference API (Qwen embedding model) with Gemini embedding fallback |
| Database | PostgreSQL |
| Vector search | pgvector with HNSW indexing |
| Keyword search | PostgreSQL full-text search with GIN indexing |
| Tool integration | Model Context Protocol (MCP), FastMCP |
| Web search | Tavily |
| PDF processing | PyMuPDF / PyMuPDFLoader |
| Python dependency management | uv |
| Frontend | HTML, CSS, JavaScript |

> **Note:** Provider models, embedding dimensions, and API availability can change. Check the configuration and provider documentation if you need to update model names or adapt the application to different service tiers.

## Repository Structure

```text
Agentic-RAG/
├── assets/
│   └── architecture.png
├── backend/
│   ├── agent/
│   │   ├── fallback/       # Fallback handling
│   │   ├── start/          # Intent classification and routing
│   │   ├── states/         # Shared LangGraph state
│   │   └── graph.py        # Main agent graph
│   ├── config/
│   │   └── config.py       # Models, prompts, database and MCP configuration
│   ├── documents/
│   │   ├── graph/          # Document discovery and ingestion workflow
│   │   └── ingestion/      # Chunking, embeddings, storage and indexes
│   ├── mcp/
│   │   ├── clients/        # MCP clients used by the agent
│   │   └── servers/        # Filesystem, database and web-search tools
│   ├── rag/
│   │   ├── generation/     # Answer paths and relevance handling
│   │   ├── refinement/     # Document classification and context refinement
│   │   └── retrieval/      # Hybrid retrieval, evaluation and RRF
│   └── app.py              # FastAPI application
├── db_setup/               # Database and table setup scripts
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── pyproject.toml
├── uv.lock
└── README.md
```

## How Retrieval Works

The RAG retrieval pipeline combines two complementary search methods:

### 1. Dense vector retrieval

Each document chunk is embedded and stored in a PostgreSQL `vector` column. At query time, the query is embedded and nearest-neighbor search ranks chunks by vector distance. This helps retrieve semantically related content even when the wording differs from the query.

### 2. Keyword retrieval

PostgreSQL full-text search uses a generated `tsvector` column and `plainto_tsquery` to find chunks matching important query terms. A GIN index supports efficient keyword lookup.

### 3. Reciprocal Rank Fusion (RRF)

The two ranked lists are combined using a reciprocal-rank score:

```text
RRF_score(document) = Σ 1 / (k + rank)
```

The implementation uses `k = 60` by default. Documents appearing near the top of either ranked list accumulate higher scores. The merged list is then passed into the downstream relevance and context-refinement workflow.

## Prerequisites

Before running the application, prepare:

- Python **3.14 or newer**, matching the project's `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/) for Python dependency and environment management.
- PostgreSQL with the **pgvector** extension available to the database administrator.
- API credentials for the model and search providers you plan to use.
- A local folder containing PDFs if you want to use local-document discovery and ingestion.

The codebase expects PostgreSQL connection URLs and provider credentials to be supplied through environment variables. The setup script creates the configured database, application user, document table, and chat tables; use an account with sufficient privileges for database/user creation and extension activation.

## Configuration

Create a `.env` file in the project root. **Do not commit real credentials.** Configure the variables used by the current code:

```dotenv
# Database administration connection (must have privileges to create users/databases
# and enable pgvector in the target database)
POSTGRES_ADMIN_URL=postgresql://<admin_user>:<password>@<host>:5432/postgres

# Application connection to the rag_db database
POSTGRES_DB_URL_RAG_DB=postgresql://<app_user>:<password>@<host>:5432/rag_db

# Used by database setup
USER_NAME=<app_user>
PASSWORD=<app_user_password>

# LLM providers
GROQ_API_KEY=<your_groq_api_key>
GOOGLE_API_KEY=<your_google_ai_api_key>

# Optional: Hugging Face embeddings provider; Gemini is used as fallback
HF_TOKEN=<your_huggingface_token>

# Web search
TAVILY_WEBSEARCH=<your_tavily_api_key>
```

Notes:

- The code reads environment variables with `python-dotenv`.
- `HF_TOKEN` is optional in the embedding implementation; when Hugging Face embedding generation fails, it attempts the Gemini embedding provider.
- Configure valid provider credentials and quotas before using model-backed features.
- The current database schema uses **2000-dimensional vectors**. The embedding provider's output dimensionality and PostgreSQL column dimension must remain consistent.
- The configured local document folder can be selected in the application's Settings UI. The backend persists this path in `settings.json` during normal operation.

## Installation and Setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/Naeem-Mubarak/Agentic-RAG.git
cd Agentic-RAG
```

Install dependencies using uv:

```bash
uv sync
```

### Initialize PostgreSQL

1. Make sure PostgreSQL is running and pgvector is installed on the server.
2. Fill in `POSTGRES_ADMIN_URL`, `POSTGRES_DB_URL_RAG_DB`, `USER_NAME`, and `PASSWORD` in `.env`.
3. Review the database setup scripts before running them. The setup routine creates a database and user, enables pgvector, and creates the document and chat tables. It requires appropriate database privileges and may not be safe to run repeatedly without adapting the existing-user/database handling.
4. Run the setup routine from the repository root:

```bash
uv run python -m db_setup.db_pipeline
```

The setup code currently uses the database name `rag_db`, document table `rag_docs`, chat table `chat_table`, and history table `chat_history`.

## Running the Application

Start the FastAPI backend from the repository root:

```bash
uv run uvicorn backend.app:app --reload
```

The API is normally available at:

- API base: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Open `frontend/index.html` in a browser to inspect the frontend. The frontend makes requests to the backend, so ensure its API base URL in `frontend/app.js` matches the address where FastAPI is running. If you change the backend host or port, update the frontend configuration accordingly.

### First-use checklist

1. Confirm the database is reachable and the schema exists.
2. Verify that provider API keys are configured.
3. Start the backend.
4. Open the frontend and use **Settings** to choose the folder containing your PDFs.
5. Ask the agent to list available files, select PDFs for ingestion when prompted, and then ask questions about the indexed documents.

## API Overview

The FastAPI application includes endpoints for chat management, folder settings, folder browsing, document upload, and message processing.

| Endpoint | Purpose |
|---|---|
| `GET /setting` | Read the configured documents folder |
| `PUT /setting` | Update the configured documents folder |
| `GET /browse-folder` | Browse subdirectories for folder selection |
| `POST /chat` | Create a chat session |
| `GET /chat_list` | List saved chat sessions |
| `GET /chat/{thread_id}` | Load a chat transcript |
| `DELETE /chat/{thread_id}` | Delete a chat session |

For the complete route schemas and any additional endpoints, run the backend and consult the interactive API documentation at `/docs`.

## Security Notes

- Keep `.env`, database passwords, and provider tokens out of version control.
- This is currently structured as a **local, single-user application**, not a hardened multi-tenant service.
- The backend's CORS configuration currently allows all origins. Restrict it before exposing the service outside a trusted development environment.
- The folder browser and document tools can access local filesystem paths supplied to the backend. Run the service with a least-privilege operating-system account and do not expose it publicly without adding authentication and path-access controls.
- Review database permissions and provider usage limits before deploying to a shared or production environment.
- Do not expose the API directly to the public internet without authentication, request validation, rate limiting, and deployment-appropriate secret management.

## Limitations and Future Improvements

Potential next steps for making the project more production-ready:

- Add authentication, authorization, and restricted filesystem access.
- Move secrets to a managed secret store for deployed environments.
- Add automated tests for routing, ingestion, retrieval, and database operations.
- Add retrieval and answer-quality evaluation with a representative test dataset.
- Make ingestion idempotent and support document updates/deletion without leaving stale chunks.
- Add structured logging, tracing, and monitoring across the LangGraph workflow.
- Improve error handling and connection lifecycle management for long-running API processes.
- Add deployment instructions and a containerized development/production setup.
- Document and validate the supported Python version and embedding-provider compatibility in CI.

## License

This project includes a [LICENSE](LICENSE) file. Review it for the applicable terms.
