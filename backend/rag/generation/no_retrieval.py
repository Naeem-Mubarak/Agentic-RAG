from backend.agent.states.states import Agent_state
from langchain_core.output_parsers import StrOutputParser
from backend.config.config import no_retrieval_response_prompt, Gemini_model_provider
from langchain_core.prompts import ChatPromptTemplate


model = Gemini_model_provider()

def no_search_response_generator(state : Agent_state):

    """
    Not all queries need vector search or web search so reducing the heavy lifting of web search and vector search
    """

    prompt = ChatPromptTemplate.from_messages([
        ('system',no_retrieval_response_prompt),
        ('human','Query: {query} \n\n History: {history}')
    ])

    parser = StrOutputParser()

    chain = prompt | model | parser

    response = chain.invoke({
        "query" : state['query'],
        "history" : state['message_history']
    })

    state['final_answer'] = response

    return state