from backend.agent.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from backend.config.config import irrelevant_generation_prompt, Gemini_model_provider
from langchain_core.output_parsers import StrOutputParser

model = Gemini_model_provider()


async def irrelvent(state: Agent_state):

    """
    Retrieved content is irrelevant, so use the refined web-search content
    and its sources to generate the answer.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", irrelevant_generation_prompt),
        ("human", """Query: {query}
        \n docs: {docs}
        \n chat_history: {history}""")
    ])

    parser = StrOutputParser()
    chain = prompt | model | parser

    web_docs = "\n\n".join(
        f"""--- Web Result {i} ---
Source: {doc['source']}
Title: {doc['metadata'].get('title', doc['source'])}
Published: {doc['metadata'].get('published_date') or 'Unknown'}

Content:
{doc['text']}"""
        for i, doc in enumerate(
            state['filtered_web_knowledge'],
            start=1
        )
    )

    response = chain.invoke({
        "query": state['query'],
        "docs": web_docs,
        "history": state['message_history']
    })

    state['final_answer'] = response

    sources = state['web_sources']
    state['final_answer'] += (
        "\n\n\nThese are the sources used during response generation\n"
    )

    for source in sources:
        state['final_answer'] += (
            f"- [{source['title']}]({source['source']})\n"
        )

    return state
