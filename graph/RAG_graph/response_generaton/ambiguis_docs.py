from graph.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from config.config import ambiguous_generation_prompt, Gemini_model_provider
from langchain_core.output_parsers import StrOutputParser

model = Gemini_model_provider()



async def ambiguis(state: Agent_state):

    """
    Retrieved content is ambiduis so picking refined web search content and it's sources combining with original retrieved refined documents
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system",ambiguous_generation_prompt),
        ("human","Query: {query} \n retrieved docs: {retrieved_docs} \n\n websearch docs: {web_docs} ")
    ])

    parser = StrOutputParser()

    chain = prompt | model | parser

    response = chain.invoke({
        "query" : state['query'],
        "retrieved_docs": state['filtered_knowledge'],   
        "web_docs": state['filtered_web_knowledge'] 
    })

    state['final_answer'] = response
    sources = state['web_sources']
    state['final_answer'] += "\n\n\nThese are some external sources used during response generation"
    for source in sources:
            state['final_answer'] += f"- [{source['title']}]({source['source']})\n"

    
    return state