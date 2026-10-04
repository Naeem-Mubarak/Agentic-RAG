from backend.agent.states.states import Agent_state
from langgraph.types import Command
from typing import Literal
from backend.documents.ingestion.data_ingestion_pipeline import loading_chunking_embedding_storing
from langgraph.graph import END



def ingest_documents(state: Agent_state) -> Command[Literal['__end__']]:

    """
    data ingestion pipeline embedded into graph node
    """

    if not state['doc_obj']:
        return Command(update=state, goto=END)

    loading_chunking_embedding_storing(state['doc_obj'])
    message = "The following documents have been successfully ingested into the database:\n\n"

    message += "\n".join(
        f"{i}. {document}"
        for i, document in enumerate(state['selected_docs'], start=1)
    )
    state['tool_response'] = message

    return Command(update=state, goto=END)
    