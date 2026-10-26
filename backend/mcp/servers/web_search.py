from datetime import date
import json
import os
import re

from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_tavily import TavilySearch


mcp = FastMCP(name="Web search")

load_dotenv()


def _get_freshness(query: str) -> str | None:
    """
    Detect explicit temporal intent and map it to Tavily's supported
    relative time ranges.
    """
    q = query.lower()

    if re.search(r"\b(today|right now|just now|as of today)\b", q):
        return "day"

    if re.search(r"\b(this week|this week'?s|past week|last week)\b", q):
        return "week"

    if re.search(r"\b(this month|past month|last month)\b", q):
        return "month"

    if re.search(
        r"\b(latest|most recent|newest|current|recent|recently|up[- ]to[- ]date)\b",
        q,
    ):
        return "year"

    return None


@mcp.tool
def websearch(query: str):
    """
    Search the web with Tavily and return a deterministic JSON payload.

    Freshness-sensitive queries are constrained to recent results and the
    current year is added to the query so that old release pages are less
    likely to outrank current information.
    """
    tavily_api_key = os.getenv("TAVILY_WEBSEARCH")

    if not tavily_api_key:
        return json.dumps(
            {
                "error": "TAVILY_WEBSEARCH environment variable is not set",
                "error_type": "ConfigurationError",
            }
        )

    freshness = _get_freshness(query)
    search_query = query.strip()

    if freshness:
        current_year = date.today().year
        if str(current_year) not in search_query:
            search_query = f"{search_query} {current_year}"

    websearch = TavilySearch(
        tavily_api_key=tavily_api_key,
        max_results=6,
        search_depth="advanced",
        time_range=freshness,
    )

    try:
        response = websearch.invoke({"query": search_query})

        if not isinstance(response, dict):
            return json.dumps(
                {
                    "results": response if isinstance(response, list) else [],
                    "query": search_query,
                },
                ensure_ascii=False,
            )

        results = response.get("results", [])

        if isinstance(results, list) and freshness:
            dated = [
                item
                for item in results
                if isinstance(item, dict) and item.get("published_date")
            ]
            undated = [
                item
                for item in results
                if isinstance(item, dict) and not item.get("published_date")
            ]

            dated.sort(
                key=lambda item: item.get("published_date", ""),
                reverse=True,
            )

            response["results"] = dated + undated

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "error_type": type(e).__name__,
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run()
