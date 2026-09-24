from graph.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from config.config import relevant_generation_prompt, Gemini_model_provider
from langchain_core.output_parsers import StrOutputParser

model = Gemini_model_provider()



async def relevent(state: Agent_state):

    """
    Retrieved content is relevant so finally generating output for user
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system",relevant_generation_prompt),
        ("human","Query: {query} \n docs: {docs}")
    ])

    # parser = StrOutputParser()

    chain = prompt | model 

    # response = chain.invoke({
    #     "query" : state['query'],
    #     "docs" : state['filtered_knowledge']
    # })

    # state['final_answer'] = response

    # return state
    response = ""

    async for chunk in chain.astream({
        "query": state["query"],
        "docs": state["filtered_knowledge"]
    }):

        if chunk.content:
            response += chunk.content

    return {
        "final_answer": response
    }