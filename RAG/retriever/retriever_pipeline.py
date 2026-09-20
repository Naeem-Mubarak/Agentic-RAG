from RAG.retriever.similarity_search import similarity_retreiver
from RAG.retriever.keyword_search import keyword_search
from RAG.retriever.RRF import RRF
from RAG.retriever.query_rewrite import query_generator


def retriever_pipeline(query: str, top_k: int = 5):

    # queries_dict = query_generator(query)

    # queries = []
    # for query in queries_dict['queries']:
    #     queries.append(query)

    # # adding original query
    # queries += query

    # similarity_docs = []
    # keyword_match_docs = []
    # for query in queries:

    #     docs_fetched_through_cosine_similarity = similarity_retreiver(query)
    #     docs_fetched_though_keyword_search = keyword_search(query)

    #     similarity_docs += docs_fetched_through_cosine_similarity
    #     keyword_match_docs += docs_fetched_though_keyword_search

    similarity_docs = similarity_retreiver(query)
    keyword_match_docs = keyword_search(query)

    complete_docs = similarity_docs + keyword_match_docs
        
    content = RRF(
        similarity_docs,
        keyword_match_docs
    )

    if len(content) > top_k:

        return content[:5]

    return content


# query = "What is DPO"
# content , complete_docs = retriever_pipeline(query)


# print(len(content))
# print(len(complete_docs))

# docs_fetched_through_cosine_similarity = similarity_retreiver(query)
# docs_fetched_though_keyword_search = keyword_search(query)

# print(type(docs_fetched_through_cosine_similarity))
# print(docs_fetched_through_cosine_similarity)
# print(type(docs_fetched_though_keyword_search))
# print(docs_fetched_though_keyword_search)