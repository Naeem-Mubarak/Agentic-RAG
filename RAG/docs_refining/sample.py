from RAG.retriever.retriever_pipeline import retriever_pipeline


query = "What is DPO"
docs = retriever_pipeline(query)
def retriever_evaluator(docs):

    