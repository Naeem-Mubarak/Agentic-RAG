from graph.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from config.config import irrelevant_generation_prompt, Gemini_model_provider
from langchain_core.output_parsers import StrOutputParser

model = Gemini_model_provider()



async def irrelvent(state: Agent_state):

    """
    Retrieved content is irrelevant so picking refined web search content and it's sources to generate answer
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system",irrelevant_generation_prompt),
        ("human","Query: {query} \n docs: {docs}")
    ])

    # parser = StrOutputParser()

    chain = prompt | model

    # response = chain.invoke({
    #     "query" : state['query'],
    #     "docs": state['filtered_web_knowledge'] 
    # })

    # state['final_answer'] = response
    # sources = state['web_sources']
    # state['final_answer'] += "\n\n\nThese are the sources used during response generation\n"
    # for source in sources:
    #     state['final_answer'] += f"- [{source['title']}]({source['source']})\n"

    # return state

    response = ""

    async for chunk in chain.astream({
        "query": state["query"],
        "docs": state["filtered_web_knowledge"]
    }):

        if chunk.content:
            response += chunk.content

    sources = state["web_sources"]

    response += "\n\n\nThese are the sources used during response generation\n"

    for source in sources:
        response += f"- [{source['title']}]({source['source']})\n"

    return {
        "final_answer": response
    }
