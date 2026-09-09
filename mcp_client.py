from langchain.mcp import MCPAdapter
import asyncio
from pathlib import Path
from fastmcp import Client
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from langchain_google_genai import ChatGoogleGenerativeAI


async def main():

    local_server = Client(Path("./File_system_server.py"))

    async with MCPAdapter(local_server) as adapter:
        tools = await adapter.list_tools()

        model = ChatGoogleGenerativeAI(model = 'gemini-3.5-flash')

        agent = create_agent(model,tools)


        response = await agent.ainvoke({
            "messages" : [
                {
                    "role" : "user",
                    "content" : "load all the documents from  /home/naeemmubarak/Desktop/RAG_documents"
                }
            ]
        })

    content = response["messages"][-1].content
    print(content[0]['text'])


if __name__ == "__main__":
    asyncio.run(main())