from pydantic import BaseModel
from typing import List
from langgraph.types import interrupt
from langchain.mcp import MCPAdapter
from langchain_core.documents import Document
from config.config import load_docs_agent_prompt,listing_files_reasoning_model
from langchain_core.prompts import ChatPromptTemplate
import json
from pathlib import Path
from fastmcp import Client
from subgraph.helper_function_for_text_extraction import extract_text
from states.states import subgraph_state
from config.config import db_connection, DB_CONNECTION_URL


listing_load_model = listing_files_reasoning_model()


class doc_selection(BaseModel):
    pdf_docs: List[str]


async def load_docs(state: subgraph_state):

    conn, cursor = db_connection(DB_CONNECTION_URL)

    # interrupting to ask user which documents he wants to load
    confirmation = interrupt({
        "type" : "confirmation",
        "question" : state['tool_response']
    })
    

    selection_prompt = ChatPromptTemplate.from_messages([
        ('system', load_docs_agent_prompt),
        ('human', "AVAILABLE DOCUMENTS:\n{available}\n\nUSER CONFIRMATION:\n{confirmation}")
    ])

    structured_llm = listing_load_model.with_structured_output(doc_selection)
    
    selection = await (selection_prompt | structured_llm).ainvoke({
        "available": state['tool_response'],
        "confirmation": confirmation
    })
    
    state['selected_docs'] = selection.pdf_docs

    cursor.execute("""SELECT DISTINCT document_name FROM rag_docs """)
    docs = cursor.fetchall()
    docs_in_db = [doc[0] for doc in docs] # decoupling and converting into list

    selected_docs = [doc for doc in state['selected_docs'] if doc not in docs_in_db]
    skipped_docs = [doc for doc in state['selected_docs'] if doc in docs_in_db]


    if skipped_docs:
        print("These documents are already in the DB")
        for i in skipped_docs:
            print(i)
        print("Skipped to avoid duplication")


    state['selected_docs'] = selected_docs

    server_path = "/home/naeemmubarak/Desktop/Agentic-RAG/MCP/file_system_server.py"
    local_Server = Client(Path(server_path))
    adapter = MCPAdapter(local_Server)


    if selected_docs:

        async with adapter:

            tools = await adapter.list_tools()

            load_tool = next(t for t in tools if t.name == "load_docs")

            response = await load_tool.ainvoke({
                "path": state['folder_path'],
                "pdf_docs": state['selected_docs']
            })
            data = json.loads(extract_text(response))


            doc_obj = []
            for doc_content in data:
                doc = []
                for page_content in doc_content:
                    page_content.pop('id',None)
                    doc.append(
                        Document(
                            page_content = page_content['page_content'],
                            metadata = page_content['metadata']
                        )
                    )
                doc_obj.append(doc)

            state['doc_obj'] = doc_obj
            return state

    state['doc_obj'] = []
    return state