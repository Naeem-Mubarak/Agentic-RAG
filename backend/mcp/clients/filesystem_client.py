from backend.config.config import agent_tool_usage_instruction,general_model,file_system_server
from langchain.messages import AIMessage, ToolMessage
from typing import Literal
import json
from pathlib import Path
from langchain.agents import create_agent
from langgraph.types import Command
from langgraph.graph import END
from backend.documents.graph.text_extraction import extract_text
from langchain.mcp import MCPAdapter
from fastmcp import Client
from backend.agent.states.states import Agent_state


listing_load_model = general_model()


# getting the mcp server
server = file_system_server()



async def File_System_MCP(state: Agent_state) -> Literal['__end__','load_docs']:


    """
    MCP client node made connection with MCP server and then an agent is defined here which do reasoning and use tools according to the query
    """


    # establishing the connection with mcp server
    local_Server = Client(Path(server))
    adapter = MCPAdapter(local_Server)

    async with adapter:

        # getting tools
        tools = await adapter.list_tools()
        listing_tools = [t for t in tools if t.name in ('list_files', 'doc_filter')]

        # creating agent
        agent = create_agent(
            listing_load_model,
            listing_tools,
            system_prompt = agent_tool_usage_instruction
        )

        result = await agent.ainvoke(({
                "messages" : [
                    {
                        "role" : "user",
                        "content": f"""User Query: {state['query']}\nDocument Action: {state['document_action']}\nFolder Path: {state['folder_path']}"""
                    }
                ]
            }))

        final_ai_text = None
        for messages in result['messages']:
        
                if isinstance(messages,ToolMessage):
        
                    if messages.name == 'list_files':
                        state['available_files'] = json.loads(extract_text(messages.content))
                        
        
                    elif messages.name == 'doc_filter':
                        state['pdf_files'] = json.loads(extract_text(messages.content))

                elif isinstance(messages,AIMessage) and messages.content:
                    final_ai_text = extract_text(messages.content)


        if final_ai_text:
            state['tool_response'] = final_ai_text

        
        if state['document_action'] == 'load' and final_ai_text:
             state['tool_response'] = final_ai_text
             return Command(update=state, goto='load_docs')

        return Command(update=state, goto=END)