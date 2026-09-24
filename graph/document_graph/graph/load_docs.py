from pydantic import BaseModel
from typing import List
from langgraph.types import interrupt
from langchain.mcp import MCPAdapter
from langchain_core.documents import Document
from config.config import load_docs_agent_prompt,general_model,file_system_server
from langchain_core.prompts import ChatPromptTemplate
import json
from pathlib import Path
from fastmcp import Client
from graph.document_graph.graph.helper_function_for_text_extraction import extract_text
from graph.states.states import Agent_state
from config.config import db_connection, DB_CONNECTION_URL

# model to do reasoning
listing_load_model = general_model()


# mcp server containing tools
server = file_system_server()


# schema the output follows
class doc_selection(BaseModel):
    pdf_docs: List[str]



async def load_docs(state: Agent_state):


    """
    Ask the user (via interrupt) which available PDFs to load, skip any already
    in the database, and load the rest into Document objects.
     
    Reads: state['tool_response'] (available files), state['folder_path']
    Writes: state['selected_docs'], state['doc_obj']
    """

    # establishing db connection 
    _, cursor = db_connection(DB_CONNECTION_URL)


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


    selected_docs = [doc for doc in state['selected_docs'] if doc.split('/')[-1] not in docs_in_db]
    skipped_docs = [doc for doc in state['selected_docs'] if doc.split('/')[-1] in docs_in_db]


    if skipped_docs:
        print("These documents are already in the DB")
        for i in skipped_docs:
            print(i)
        print("Skipped to avoid duplication")


    state['selected_docs'] = selected_docs

    local_Server = Client(Path(server))
    adapter = MCPAdapter(local_Server)

    load_errors = []
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
            load_errors = data.get('errors', [])

            doc_obj = []
            for doc_content in loaded_docs:
                doc = []
                for page_content in doc_content:
                    doc.append(
                        Document(
                            page_content = page_content['page_content'],
                            metadata = page_content['metadata']
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