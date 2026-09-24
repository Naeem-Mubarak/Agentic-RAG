from graph.states.states import Agent_state
from langchain.mcp import MCPAdapter
from langchain.agents import create_agent
from config.config import db_server, db_agent_prompt, general_model
from fastmcp import Client
from pathlib import Path
from langchain.messages import AIMessage


model = general_model()


async def DB_mcp(state: Agent_state):

    """
    Doing web search using websearch mcp server and fetching out the tool response instead of AI response because AI response is summary and Tool response is document fetched from sources
    """

    server = db_server()
    local_server = Client(Path(server))
    adapter = MCPAdapter(local_server)

    async with adapter:

        tools = await adapter.list_tools()
        agent = create_agent(
                    model,
                    tools,
                    system_prompt = db_agent_prompt
                )
        result = await agent.ainvoke(({
                "messages" : [
                    {
                        "role" : "user",
                        "content" : f"""User Query: {state['query']}"""
                    }
                ]
        }))

        for i in result['messages']:
            if isinstance(i,AIMessage):
                if i.content:
                    state['tool_response'] = i.content

        return state