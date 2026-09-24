from graph.states.states import Agent_state
from langchain.mcp import MCPAdapter
from langchain.agents import create_agent
from config.config import websearch_server, websearch_prompt, general_model
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Literal
from fastmcp import Client
from pathlib import Path
import json



model = general_model()


async def web_search(state: Agent_state) -> Command[Literal['knoweldge_refinement']]:

    """
    Doing web search using websearch mcp server and fetching out the tool response instead of AI response because AI response is summary and Tool response is document fetched from sources
    """

    server = websearch_server()
    local_server = Client(Path(server))
    adapter = MCPAdapter(local_server)

    async with adapter:

        tools = await adapter.list_tools()
        agent = create_agent(
                    model,
                    tools,
                    system_prompt = websearch_prompt
                )
        result = await agent.ainvoke(({
                "messages" : [
                    {
                        "role" : "user",
                        "content" : f"""User Query: {state['query']}"""
                    }
                ]
        }))

        source_title = []
        web_searched_content = []
        for message in result['messages']:
            if isinstance(message,ToolMessage):
                for i in message.content:
                    m = json.loads(i['text'])
                    for content in m['results']:
                        source_title.append({
                            "source" : content['url'],
                            "title" : content['title']
                        })
                        web_searched_content.append(content['content'])

        state['web_sources'] = source_title
        state['websearch'] = web_searched_content

        return Command(update=state, goto='knoweldge_refinement')