from pydantic import BaseModel
from typing import List,Literal
from backend.graph.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command
from backend.config.config import knowledge_filter_prompt, general_model
import re

model = general_model()


class filtered_knowledge(BaseModel):

    useful_sentence : List[str]



def decompose_strips(text: str) -> list[str]:

    """
    Splitting paragrph into sentence
    """
    joined = " ".join(text)
    joined = re.sub(r"\s+", " ",joined).strip()
    sentences = re.split(r"(?<=[.!?])\s+",joined)
    return [s.strip() for s in sentences if len(s.strip())>20]




def _refine(query: str, texts: list[str]) -> List[str]:

    strips = decompose_strips(texts)
    
    prompt = ChatPromptTemplate.from_messages([
        ('system',knowledge_filter_prompt),
        ('human','Query: {query} \n list of sentences : {sentences}')
    ])

    structured_llm = model.with_structured_output(filtered_knowledge)

    chain = prompt | structured_llm
    response = chain.invoke({
        "query" : query,
        "sentences" : strips
    })

    return response.useful_sentence


  

def knoweldge_refinement(state: Agent_state) -> Command[Literal['relevant', 'not_relevant', 'ambiguis']]:

    """
    Refines whichever knowledge source(s) this branch needs — retrieved docs for
    'relevant', web search results for 'irrelevant', both (kept separate) for
    'ambiguis' — then routes to the matching generation node.
    """

    if state['doc_class'] == 'relevant':
        docs = [doc['content'] for doc in state['retrieved_docs']]
        state['filtered_knowledge'] = _refine(state['query'], docs)
        next_node = 'relevant'

    elif state['doc_class'] == 'irrelevant':
        state['filtered_web_knowledge'] = _refine(state['query'], state['websearch'])
        next_node = 'not_relevant'

    else:  # ambiguis
        doc_texts = [doc['content'] for doc in state['retrieved_docs']]
        state['filtered_knowledge'] = _refine(state['query'], doc_texts)
        state['filtered_web_knowledge'] = _refine(state['query'], state['websearch'])
        next_node = 'ambiguis'

    return Command(update=state, goto=next_node)