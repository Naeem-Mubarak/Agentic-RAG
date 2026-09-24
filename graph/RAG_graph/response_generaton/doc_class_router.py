from typing import Literal
from graph.states.states import Agent_state



def doc_class_router(state: Agent_state) -> Literal['knoweldge_refinement', 'websearch']:
    """
    Relevant content is already gathered (retrieved_docs) — go straight to refinement.
    Irrelevant and ambiguous both need web search content first.
    """
    if state['doc_class'] == 'relevant':
        return 'knoweldge_refinement'
    return 'websearch'