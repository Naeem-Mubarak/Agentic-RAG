from datetime import date
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


def _is_freshness_query(query: str) -> bool:
    return _get_freshness(query) is not None


@mcp.tool
def websearch(query: str):
    """
    Web search using Tavily.

    Freshness-sensitive queries are explicitly constrained to recent results
    and the current year is added to the search query so that requests such as
    "latest AI model" do not compete equally with old release pages.
    """
    tavily_api_key = os.getenv("TAVILY_WEBSEARCH")

    freshness = _get_freshness(query)
    search_query = query.strip()

    if freshness:
        current_year = date.today().year

        # Give Tavily explicit temporal context. Do not replace the user's
        # query; only add the current year for freshness-sensitive searches.
        if str(current_year) not in search_query:
            search_query = f"{search_query} {current_year}"

    websearch = TavilySearch(
        tavily_api_key=tavily_api_key,
        max_results=6,
        search_depth="advanced",
        time_range=freshness,
    )

    try:
        response = websearch.invoke({
            "query": search_query
        })

        if not isinstance(response, dict):
            return response

        results = response.get("results", [])

        if isinstance(results, list):
            # Tavily normally returns published_date when the source exposes
            # one. For freshness-sensitive queries, prefer newer dated results
            # while preserving results whose publication date is unavailable.
            if freshness:
                dated = [
                    item for item in results
                    if isinstance(item, dict) and item.get("published_date")
                ]
                undated = [
                    item for item in results
                    if isinstance(item, dict) and not item.get("published_date")
                ]

                dated.sort(
                    key=lambda item: item.get("published_date", ""),
                    reverse=True,
                )

                response["results"] = dated + undated

        return response

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


if __name__ == "__main__":
    mcp.run()
