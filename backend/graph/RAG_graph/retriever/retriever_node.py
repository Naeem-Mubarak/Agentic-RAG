from backend.graph.states.states import Agent_state
from typing import Literal
from backend.graph.RAG_graph.retriever.retriever_pipeline import retriever_pipeline
from langgraph.types import Command
from langgraph.graph import END


def retriever(state: Agent_state) -> Command[Literal['retriever_evaluator']]:

    retrieve_docs = retriever_pipeline(state['query'])

    state['retrieved_docs'] = retrieve_docs

    return Command(update=state, goto='retriever_evaluator')