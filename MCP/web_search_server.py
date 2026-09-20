from fastmcp import FastMCP
from langchain_tavily import TavilySearch
from config.config import TAVILY_WEBSEARCH
mcp = FastMCP(name = "Web search")



@mcp.tool
def websearch(query: str):

    websearch = TavilySearch(
        tavily_api_key = TAVILY_WEBSEARCH,
        max_results=2
    )

    results = websearch.invoke({
        "query" : query
    })
    results_list = []
    for content in results['results']:
        results_list.append({
            "metadata" : {
                "source" : content['url'],
                "title" : content['title']
            },
            "content" : content['content'],
            "score" : content['score']
        }) 

    return results_list

