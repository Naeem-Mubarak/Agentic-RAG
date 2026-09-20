from states.states import subgraph_state
from langgraph.types import Command
from typing import Literal
from data_ingestion.data_ingestion_pipeline import loading_chunking_embedding_storing
from langgraph.graph import END



def ingest_documents(state: subgraph_state) -> Command[Literal['__end__']]:

    if not state['doc_obj']:
        return Command(update=state, goto=END)

    loading_chunking_embedding_storing(state['doc_obj'])
    print("Congratualtion everything is working great")

    return Command(update=state, goto=END)
    