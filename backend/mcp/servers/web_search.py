from fastmcp import FastMCP
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
import os
import json

mcp = FastMCP(name = "Web search")

load_dotenv()

@mcp.tool
def websearch(query: str):

    """
    Websearch tool using tavily take a query and then searches the internet and find it's relevent data
    """
    TAVILY_WEBSEARCH = os.getenv("TAVILY_WEBSEARCH")
    websearch = TavilySearch(
        tavily_api_key = TAVILY_WEBSEARCH,
        max_results=2
    )

    try:
        results = websearch.invoke({
            "query": query
        })

        return results

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }



if __name__ == "__main__":
    mcp.run()

