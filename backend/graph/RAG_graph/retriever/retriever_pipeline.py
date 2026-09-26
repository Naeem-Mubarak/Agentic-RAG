from backend.graph.RAG_graph.retriever.similarity_search import similarity_retreiver
from backend.graph.RAG_graph.retriever.keyword_search import keyword_search
from backend.graph.RAG_graph.retriever.RRF import RRF


def retriever_pipeline(query: str, top_k: int = 5):

    """
    Retriever pipeline getting docs from similarity retriever and keyword retriever and then doing RRF to get top k documents 
    """

    similarity_docs = similarity_retreiver(query)
    keyword_match_docs = keyword_search(query)
        
    content = RRF(
        similarity_docs,
        keyword_match_docs
    )

    if len(content) > top_k:

        return content[:5]

    return content
