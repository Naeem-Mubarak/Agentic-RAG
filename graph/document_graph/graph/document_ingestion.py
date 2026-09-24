from graph.states.states import Agent_state
from langgraph.types import Command
from typing import Literal
from graph.document_graph.data_ingestion.data_ingestion_pipeline import loading_chunking_embedding_storing
from langgraph.graph import END



def ingest_documents(state: Agent_state) -> Command[Literal['__end__']]:

    """
    data ingestion pipeline embedded into graph node
    """

    if not state['doc_obj']:
        return Command(update=state, goto=END)

    loading_chunking_embedding_storing(state['doc_obj'])
    print("document stored in DB successfully")

    return Command(update=state, goto=END)
    