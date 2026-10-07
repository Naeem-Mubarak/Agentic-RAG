import json
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg2 import sql
from psycopg2.extras import Json

from langgraph.types import Command
from langchain_community.document_loaders import PyMuPDFLoader

from backend.agent.graph import graph
from backend.agent.states.initial_state import build_initial_state
from backend.config.config import (
    db_connection, DB_CONNECTION_URL, CHAT_TABLE, CHAT_HISTORY, TABLE_NAME
)
from backend.documents.graph.document_ingestion import loading_chunking_embedding_storing
from backend.agent.start.confirmation_check import is_confirmation


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

conn, cursor = db_connection(DB_CONNECTION_URL)

# Documents folder -- a single global setting, since this is a personal,
# single-user local tool, not a multi-tenant product. Every chat shares it.
# Persisted to a small file, not just an in-memory variable -- uvicorn's
# --reload restarts the process on every file save (which happens constantly
# during active development), and an in-memory-only global would silently
# wipe this back to None on every single restart.
SETTINGS_FILE = Path("settings.json")


def _load_folder_path() -> str | None:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text()).get("folder_path")
        except Exception:
            return None
    return None


def _save_folder_path(path: str):
    SETTINGS_FILE.write_text(json.dumps({"folder_path": path}))


folder_path: str | None = _load_folder_path()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Nodes whose LLM output should be streamed token-by-token to the client.
# Everything else (classification, tool-calling agents, confirmation checks)
# runs silently -- only these three ever produce a user-facing generated answer.
STREAMING_NODES = ("relevant", "not_relevant", "ambiguis", "no_search_response")

# Human-readable labels for the "agent working" indicator -- one entry per
# REAL node in the graph. Nothing invented here: each label only ever shows
# up because that exact node actually started running, reported live via
# astream_events' on_chain_start. A query that never visits a node (e.g. a
# plain chat question never touches File_System_MCP) never shows its label.
NODE_STAGE_LABELS = {
    "intent_classifier": "Understanding your request",
    "retriever": "Searching your documents",
    "retriever_evaluator": "Evaluating relevance",
    "doc_classification": "Classifying results",
    "knoweldge_refinement": "Refining retrieved context",
    "websearch": "Searching the web",
    "relevant": "Generating response",
    "not_relevant": "Generating response",
    "ambiguis": "Generating response",
    "File_System_MCP": "Accessing your files",
    "load_docs": "Loading document",
    "data_ingestion": "Indexing document",
    "DB_MCP": "Checking the database",
    "no_search_response": "Preparing response",
    "no_path_found": "Checking folder access",
}


# ============================================================
# Settings
# ============================================================

class PathSchema(BaseModel):
    folder_path: str


@app.get("/setting")
def get_folder_path():
    return {"folder_path": folder_path}


@app.put("/setting")
def set_folder_path(data: PathSchema):
    global folder_path
    folder_path = data.folder_path
    _save_folder_path(folder_path)
    return {"folder_path": folder_path}


@app.get("/browse-folder")
def browse_folder(path: str | None = None):
    """
    Lists subdirectories of a given path, for an in-app folder browser.

    Deliberately NOT a native OS dialog (tkinter) -- that needs a GUI display
    on the machine running the backend, which fails outright over SSH, in a
    headless container, in WSL without an X server, or any environment
    without an active display. Plain directory listing over HTTP works
    identically everywhere the backend runs, with no extra dependency.
    """
    current = Path(path) if path else Path.home()

    if not current.exists() or not current.is_dir():
        raise HTTPException(status_code=400, detail=f"'{current}' is not a valid folder")

    try:
        directories = sorted(
            (p.name for p in current.iterdir() if p.is_dir() and not p.name.startswith('.')),
            key=str.lower
        )
    except PermissionError:
        directories = []

    parent = str(current.parent) if current != current.parent else None

    return {
        "current_path": str(current),
        "parent_path": parent,
        "directories": directories
    }


# ============================================================
# Chat management
# ============================================================

@app.post("/chat")
def create_chat():
    thread_id = str(uuid.uuid4())
    cursor.execute(
        sql.SQL("INSERT INTO {} (thread_id, title) VALUES (%s, %s)").format(
            sql.Identifier(CHAT_TABLE)
        ),
        (thread_id, "New chat")
    )
    return {"thread_id": thread_id, "title": "New chat"}


@app.get("/chat_list")
def chat_list():
    try:
        cursor.execute(
            sql.SQL("SELECT thread_id, title, created_at FROM {} ORDER BY created_at DESC").format(
                sql.Identifier(CHAT_TABLE)
            )
        )
        rows = cursor.fetchall()
        return [
            {"thread_id": tid, "title": title, "created_at": created_at.isoformat()}
            for tid, title, created_at in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{thread_id}")
def load_chat(thread_id: str):
    try:
        cursor.execute(
            sql.SQL("""
                SELECT query, response FROM {}
                WHERE thread_id = %s
                ORDER BY created_at ASC
            """).format(sql.Identifier(CHAT_HISTORY)),
            (thread_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "query": query.get("content", "") if isinstance(query, dict) else query,
                "response": response.get("content", "") if isinstance(response, dict) else response,
            }
            for query, response in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{thread_id}")
def delete_chat(thread_id: str):
    try:
        cursor.execute(
            sql.SQL("DELETE FROM {} WHERE thread_id = %s").format(sql.Identifier(CHAT_TABLE)),
            (thread_id,)
        )
        # chat_history rows are removed automatically via ON DELETE CASCADE
        return {"message": "Chat deleted successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# History helpers -- shared by the streaming endpoint
# ============================================================

def load_history_as_text(thread_id: str) -> str:
    """
    Reformats this chat's stored turns into a plain, readable transcript
    string for the generation prompts (which embed {history} as plain text,
    not as a structured message list).
    """
    cursor.execute(
        sql.SQL("""
            SELECT query, response FROM {}
            WHERE thread_id = %s
            ORDER BY created_at ASC
        """).format(sql.Identifier(CHAT_HISTORY)),
        (thread_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        return ""

    lines = []
    for query, response in rows:
        q_text = query.get("content", "") if isinstance(query, dict) else (query or "")
        r_text = response.get("content", "") if isinstance(response, dict) else (response or "")
        lines.append(f"User: {q_text}")
        if r_text:
            lines.append(f"Assistant: {r_text}")

    return "\n".join(lines)


def save_turn(thread_id: str, query_text: str, response_text: str):
    """
    Stores one turn as a Human/AI message pair. Columns are JSONB, so dicts
    must go through psycopg2's Json() adapter -- passing a raw dict directly
    fails, since psycopg2 has no default adapter for a plain Python dict.
    """
    query_payload = {"type": "human", "content": query_text}
    response_payload = {"type": "ai", "content": response_text}

    cursor.execute(
        sql.SQL("INSERT INTO {} (thread_id, query, response) VALUES (%s, %s, %s)").format(
            sql.Identifier(CHAT_HISTORY)
        ),
        (thread_id, Json(query_payload), Json(response_payload))
    )


def maybe_set_title(thread_id: str, query_text: str):
    """First message in a chat becomes its sidebar title."""
    cursor.execute(
        sql.SQL("UPDATE {} SET title = %s WHERE thread_id = %s AND title = 'New chat'").format(
            sql.Identifier(CHAT_TABLE)
        ),
        (query_text[:40], thread_id)
    )


async def get_pending_question(config: dict) -> str | None:
    """
    Derives "is this thread waiting on a confirmation" fresh from the graph's
    own persisted state. snapshot.next (a tuple of pending node names) is a
    stable, core StateSnapshot field -- if it's non-empty, the graph is
    paused. The question itself is read straight from snapshot.values rather
    than from interrupt metadata, since load_docs builds its interrupt value
    directly from state['tool_response'] -- this sidesteps LangGraph's
    interrupt-object API, whose exact attribute shape has moved between
    versions and can't be verified without running the target environment.
    """
    snapshot = await graph.aget_state(config)
    if snapshot.next:
        return snapshot.values.get('tool_response')
    return None


# ============================================================
# The actual conversation endpoint -- SSE streaming
# ============================================================

class MessageSchema(BaseModel):
    thread_id: str
    message: str


async def sse_event(msg_type: str, **fields) -> str:
    return f"data: {json.dumps({'type': msg_type, **fields})}\n\n"


@app.post("/message-stream")
async def message_stream(data: MessageSchema):

    async def event_generator():
        thread_id = data.thread_id
        user_message = data.message
        config = {"configurable": {"thread_id": thread_id}}

        try:
            pending_question = await get_pending_question(config)

            if pending_question and is_confirmation(pending_question, user_message):
                graph_input = Command(resume=user_message)
            else:
                history_text = load_history_as_text(thread_id)
                graph_input = build_initial_state(user_message, folder_path, history_text)

            state = None
            seen_stages = set()

            async for event in graph.astream_events(graph_input, config, version="v2"):
                node = event.get("metadata", {}).get("langgraph_node")

                # Real-time "agent working" stage -- fires once per node that
                # actually runs, the first time it starts. Never fabricated:
                # if a node doesn't run for this query, its label never appears.
                if event["event"] == "on_chain_start" and node in NODE_STAGE_LABELS and node not in seen_stages:
                    seen_stages.add(node)
                    yield await sse_event("stage", content=NODE_STAGE_LABELS[node])

                if event["event"] != "on_chat_model_stream":
                    continue
                if node not in STREAMING_NODES:
                    continue
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield await sse_event("token", content=chunk.content)

            snapshot = await graph.aget_state(config)
            state = snapshot.values

            if snapshot.next:
                pending = state.get('tool_response')
                yield await sse_event("interrupt", content=pending)
                maybe_set_title(thread_id, user_message)
                save_turn(thread_id, user_message, pending)
                yield await sse_event("done")
                return

            if state.get('intent') in ('document', 'DB'):
                response_text = state.get('tool_response', '')
                yield await sse_event("message", content=response_text)
            else:
                # 'RAG' intent -- already streamed token-by-token above
                response_text = state.get('final_answer', '')

                # Sources -- built only from data the pipeline already
                # computed for this exact answer. Never fabricated: a
                # document-only answer lists the real filenames its chunks
                # came from; a web-assisted answer lists the real search
                # results already attached to state['web_sources'].
                sources = []
                seen_names = set()
                for doc in state.get('retrieved_docs') or []:
                    name = doc.get('source')
                    if name and name not in seen_names:
                        seen_names.add(name)
                        sources.append({"type": "document", "name": name})
                for src in state.get('web_sources') or []:
                    sources.append({"type": "web", "name": src.get('title'), "url": src.get('source')})

                if sources:
                    yield await sse_event("sources", items=sources)

            maybe_set_title(thread_id, user_message)
            save_turn(thread_id, user_message, response_text)

            yield await sse_event("done")

        except Exception as e:
            yield await sse_event("error", message=str(e))
            yield await sse_event("done")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ============================================================
# Document upload -- ingests immediately, no separate "load" step needed
# ============================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF files only")

    # Skip re-ingesting a file that's already in the vector store.
    cursor.execute(
        sql.SQL("SELECT 1 FROM {} WHERE document_name = %s LIMIT 1").format(
            sql.Identifier(TABLE_NAME)
        ),
        (file.filename,)
    )
    if cursor.fetchone():
        return {"message": f"'{file.filename}' is already in the database -- skipped."}

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        loader = PyMuPDFLoader(file_path=str(file_path))
        docs = loader.load()
        loading_chunking_embedding_storing([docs])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not process '{file.filename}': {e}")

    return {"message": f"'{file.filename}' stored in the database"}


# ============================================================
# Standalone message-save endpoint (kept for direct/manual use)
# ============================================================

class ResponseSchema(BaseModel):
    thread_id: str
    query: str
    response: str


@app.post("/message")
def save_message(data: ResponseSchema):
    try:
        save_turn(data.thread_id, data.query, data.response)
        return {"message": "Message saved successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
