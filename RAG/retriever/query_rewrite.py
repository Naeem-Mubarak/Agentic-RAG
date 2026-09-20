from config.config import model_provider, query_generator_prompt
from typing import TypedDict, List
from langchain_core.prompts import ChatPromptTemplate


class query_schema(TypedDict):

    queries : List[str]


model = model_provider()

def query_generator(query: str):

    """Generating 2 more queires related to original query to handle any ambiduity and catching more perspective"""

    prompt = ChatPromptTemplate.from_messages([
        ('system',query_generator_prompt),
        ('human',"Original query: {query}")
    ])

    structured_llm = model.with_structured_output(query_schema)
    chain = prompt | structured_llm

    results = chain.invoke({
        "query" : query
    })

    return results


