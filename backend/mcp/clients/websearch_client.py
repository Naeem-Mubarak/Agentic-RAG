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
import re


model = general_model()


def _extract_results(value) -> list[dict]:
    """
    Normalize the different content shapes that can arrive through MCP.

    The web-search server returns JSON text, but MCP clients may expose that
    text as a string, a text content block, a list of content blocks, or
    occasionally a decoded Python object.
    """
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Web search tool returned non-JSON text: {value[:500]}"
            ) from e

        return _extract_results(parsed)

    if isinstance(value, dict):
        # Normal Tavily payload.
        if "results" in value:
            results = value["results"]

            if not isinstance(results, list):
                raise TypeError(
                    "Web search returned a non-list 'results' field"
                )

            return [
                item for item in results
                if isinstance(item, dict)
            ]

        # MCP text content block.
        if value.get("type") == "text" and "text" in value:
            return _extract_results(value["text"])

        if "error" in value:
            raise RuntimeError(
                f"Web search tool failed: "
                f"{value.get('error_type', 'UnknownError')}: "
                f"{value['error']}"
            )

        # Some MCP wrappers use a nested content/text field.
        if "text" in value:
            return _extract_results(value["text"])

        if "content" in value:
            return _extract_results(value["content"])

        # A single Tavily result can also arrive directly.
        if value.get("url") and value.get("content"):
            return [value]

        raise ValueError(
            "Web search tool returned an unexpected object. "
            f"Expected Tavily results, got keys: {list(value.keys())}"
        )

    if isinstance(value, list):
        # A list may be either:
        # 1. MCP content blocks, or
        # 2. Tavily result dictionaries.
        results = []

        for item in value:
            if isinstance(item, dict) and item.get("url") and item.get("content"):
                results.append(item)
                continue

            results.extend(_extract_results(item))

        return results

    raise TypeError(
        f"Unsupported web search response type: {type(value).__name__}"
    )


def _is_latest_query(query: str) -> bool:
    q = query.lower()
    return bool(
        re.search(
            r"\b(latest|most recent|newest)\b", q
        )
    )


def _date_key(value) -> str:
    if not value:
        return ""
    return str(value)[:10]


def _rank_results_for_query(query: str, results: list[dict]) -> list[dict]:
    """
    Enforce deterministic freshness for latest/most-recent questions.

    The LLM may rank results by semantic relevance, which can select an old
    page over a newer release. For explicit latest queries, only dated results
    are eligible and the newest dated results are passed downstream.
    """
    if not _is_latest_query(query):
        return results

    dated = [
        item for item in results
        if item.get("published_date")
    ]

    dated.sort(
        key=lambda item: _date_key(item.get("published_date")),
        reverse=True,
    )

    # Keep the newest few candidates so generation can still compare them,
    # while preventing stale undated/old results from dominating the answer.
    return dated[:3]


async def web_search(
    state: Agent_state
) -> Command[Literal["knoweldge_refinement"]]:
    """
    Run the web-search MCP agent and keep the actual web documents rather
    than the agent's natural-language summary.
    """
    server = websearch_server()
    local_server = Client(Path(server))
    adapter = MCPAdapter(local_server)

    async with adapter:
        tools = await adapter.list_tools()

        agent = create_agent(
            model,
            tools,
            system_prompt=websearch_prompt,
        )

        result = await agent.ainvoke({
            "messages": [
                {
                    "role": "user",
                    "content": f"User Query: {state['query']}",
                }
            ]
        })

        collected_results = []
        seen_urls = set()

        for message in result["messages"]:
            if not isinstance(message, ToolMessage):
                continue

            results = _extract_results(message.content)

            for content in results:
                url = content.get("url")
                text = content.get("content") or content.get("raw_content")
                if not url or not text or url in seen_urls:
                    continue

                seen_urls.add(url)
                collected_results.append({
                    "url": url,
                    "title": content.get("title") or url,
                    "content": text,
                    "published_date": content.get("published_date"),
                })

        collected_results = _rank_results_for_query(
            state["query"],
            collected_results,
        )

        source_title = []
        websearch_docs = []

        for content in collected_results:
            url = content["url"]
            title = content["title"]
            text = content["content"]
            published_date = content.get("published_date")

            source_title.append({
                "source": url,
                "title": title,
                "published_date": published_date,
            })

            websearch_docs.append({
                "content": text,
                "source": url,
                "page_number": None,
                "metadata": {
                    "title": title,
                    "published_date": published_date,
                },
            })

        if not websearch_docs:
            raise RuntimeError(
                "Web search completed but returned no usable search results."
            )

        state["web_sources"] = source_title
        state["websearch"] = websearch_docs

        return Command(
            update=state,
            goto="knoweldge_refinement",
        )
