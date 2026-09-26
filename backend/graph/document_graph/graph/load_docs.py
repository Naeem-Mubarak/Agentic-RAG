from pydantic import BaseModel
from typing import List
from langgraph.types import interrupt
from langchain.mcp import MCPAdapter
from langchain_core.documents import Document
from backend.config.config import load_docs_agent_prompt, general_model, file_system_server
from langchain_core.prompts import ChatPromptTemplate
import json
import difflib
from pathlib import Path
from fastmcp import Client
from backend.graph.document_graph.graph.helper_function_for_text_extraction import extract_text
from backend.graph.states.states import Agent_state
from backend.config.config import db_connection, DB_CONNECTION_URL, TABLE_NAME
from psycopg2 import sql

# model to do reasoning
listing_load_model = general_model()


# mcp server containing tools
server = file_system_server()


# schema the output follows
class doc_selection(BaseModel):
    pdf_docs: List[str]


def resolve_to_real_filename(selected: str, available: list[str]) -> str | None:
    """
    Maps a model-selected filename back onto the exact, byte-accurate string
    from disk. Needed because natural-language generation can silently
    substitute characters (a plain hyphen becoming a typographic one, straight
    quotes becoming curly quotes) even when asked to copy text verbatim --
    which looks identical to a human but breaks a direct filesystem lookup.
    """
    if selected in available:
        return selected
    matches = difflib.get_close_matches(selected, available, n=1, cutoff=0.85)
    return matches[0] if matches else None


async def load_docs(state: Agent_state):
    """
    Ask the user (via interrupt) which available PDFs to load, skip any already
    in the database, and load the rest into Document objects.

    Reads: state['pdf_files'] (available files, exact from disk), state['folder_path']
    Writes: state['selected_docs'], state['doc_obj']
    """

    # establishing db connection
    _, cursor = db_connection(DB_CONNECTION_URL)

    # interrupting to ask user which documents he wants to load
    confirmation = interrupt({
        "type": "confirmation",
        "question": state['tool_response']
    })

    selection_prompt = ChatPromptTemplate.from_messages([
        ('system', load_docs_agent_prompt),
        ('human', "AVAILABLE DOCUMENTS:\n{available}\n\nUSER CONFIRMATION:\n{confirmation}")
    ])

    structured_llm = listing_load_model.with_structured_output(doc_selection)

    # Feed the model the RAW filenames from disk, not the natural-language
    # listing text in tool_response -- prose generation can subtly rewrite
    # punctuation (hyphens, quotes) that then no longer matches the real file.
    available_list = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(state['pdf_files']))

    selection = await (selection_prompt | structured_llm).ainvoke({
        "available": available_list,
        "confirmation": confirmation
    })

    # Safety net: snap whatever the model produced back onto an exact, real
    # filename, in case any residual text corruption still slipped through.
    resolved = []
    unresolved = []
    for name in selection.pdf_docs:
        match = resolve_to_real_filename(name, state['pdf_files'])
        if match:
            resolved.append(match)
        else:
            unresolved.append(name)

    state['selected_docs'] = resolved

    cursor.execute(
        sql.SQL("""SELECT DISTINCT document_name FROM {}""").format(sql.Identifier(TABLE_NAME))
    )
    docs = cursor.fetchall()
    docs_in_db = [doc[0] for doc in docs]  # decoupling and converting into list

    selected_docs = [doc for doc in state['selected_docs'] if doc.split('/')[-1] not in docs_in_db]
    skipped_docs = [doc for doc in state['selected_docs'] if doc.split('/')[-1] in docs_in_db]

    if skipped_docs:
        state["tool_response"] = (
            "The following documents are already in the DB:\n"
            + "\n".join(f"- {doc}" for doc in skipped_docs)
            + "\n\nSkipped to avoid duplication."
        )

    state['selected_docs'] = selected_docs

    local_Server = Client(Path(server))
    adapter = MCPAdapter(local_Server)

    load_errors = [
        {"file": name, "error": "Could not match to an available file"}
        for name in unresolved
    ]
    doc_obj = []

    if selected_docs:

        async with adapter:

            tools = await adapter.list_tools()

            load_tool = next(t for t in tools if t.name == "load_docs")

            response = await load_tool.ainvoke({
                "path": state['folder_path'],
                "pdf_docs": state['selected_docs']
            })
            data = json.loads(extract_text(response))
            loaded_docs = data.get('documents', [])
            load_errors += data.get('errors', [])

            for doc_content in loaded_docs:
                doc = []
                for page_content in doc_content:
                    doc.append(
                        Document(
                            page_content=page_content['page_content'],
                            metadata=page_content['metadata']
                        )
                    )
                doc_obj.append(doc)

    state['doc_obj'] = doc_obj

    if load_errors:
        state['tool_response'] = json.dumps({
            "loaded": len(doc_obj),
            "errors": load_errors
        }, indent=2)

    return state
