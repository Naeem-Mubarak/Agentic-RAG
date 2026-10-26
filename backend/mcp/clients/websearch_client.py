from backend.agent.states.states import Agent_state
from langchain.mcp import MCPAdapter
from langchain.agents import create_agent
from backend.config.config import websearch_server, websearch_prompt, general_model
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

def _extract_results(value) -> list[dict]:
    """
    Normalize MCP tool output into Tavily's results list.

    FastMCP/MCPAdapter can represent a returned Python dict as a text
    content block, while other versions may expose the dict directly.
    Never assume one transport representation.
    """
    if isinstance(value, dict):
        if "results" in value:
            results = value["results"]
            if isinstance(results, list):
                return results
            raise TypeError("Web search returned a non-list 'results' field")

        if "error" in value:
            raise RuntimeError(
                f"Web search tool failed: {value.get('error_type', 'UnknownError')}: "
                f"{value['error']}"
            )

        if "text" in value:
            return _extract_results(value["text"])

        if "content" in value:
            return _extract_results(value["content"])

        raise ValueError(
            f"Web search tool returned an unexpected object. "
            f"Expected 'results', got keys: {list(value.keys())}"
        )

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Web search tool returned non-JSON text: {value[:300]}"
            ) from e
        return _extract_results(parsed)

    if isinstance(value, list):
        results = []
        for item in value:
            results.extend(_extract_results(item))
        return results

    raise TypeError(
        f"Unsupported web search response type: {type(value).__name__}"
    )


        source_title = []
        websearch_docs = []

        for message in result['messages']:
            if not isinstance(message, ToolMessage):
                continue

            results = _extract_results(message.content)

            for content in results:
                if not isinstance(content, dict):
                    continue

                url = content.get("url")
                title = content.get("title")
                text = content.get("content")

                if not url or not text:
                    continue

                source_title.append({
                    "source": url,
                    "title": title or url
                })
                websearch_docs.append({
                    "content": text,
                    "source": url,
                    "page_number": None,
                    "metadata": {"title": title or url}
                })

        if not websearch_docs:
            raise RuntimeError(
                "Web search completed but returned no usable search results."
            )

        state['web_sources'] = source_title
        state['websearch'] = websearch_docs

        return Command(update=state, goto='knoweldge_refinement')