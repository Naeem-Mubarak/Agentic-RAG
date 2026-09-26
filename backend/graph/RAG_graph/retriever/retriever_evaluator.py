from backend.graph.states.states import Agent_state
from langgraph.types import Command
from langchain_core.prompts import ChatPromptTemplate
from typing import Literal,List
from backend.config.config import retriever_evaluator_prompt, general_model
from pydantic import BaseModel


model = general_model()


class chunk_score(BaseModel):
    score: float

class evaluator_score(BaseModel):

    score : List[chunk_score]


def retriever_evaluator(state: Agent_state) -> Command[Literal['doc_classification']]:

    prompt = ChatPromptTemplate.from_messages([
        ('system',retriever_evaluator_prompt),
        ('human',"Query: {query} \n retrieved docs: {docs}")
    ])

    structured_llm = model.with_structured_output(evaluator_score)
    chain = prompt | structured_llm

    try:

        response = chain.invoke({
            "query" : state['query'],
            "docs" : state['retrieved_docs']
        })
        state['retrieval_score'] = [c.score for c in response.score]
        return Command(update=state, goto='doc_classification')
    
    except Exception as e:

        print(f"retriever_evaluator failed, treating as ambiguous: {e}")
        state['retrieval_score'] = []
        state['doc_class'] = 'ambiguis'
        return Command(update=state, goto='websearch')