from data_ingestion.doc_splitter import chunks_of_docs
from data_ingestion.embedding_generation import embedding_chunks
from data_ingestion.vector_store import vector_store
from data_ingestion.indexes import create_HNSW_index, GIN_index
from config.config import TABLE_NAME

def loading_chunking_embedding_storing(documents: list, table_name: str = TABLE_NAME) -> None:

    docs = chunks_of_docs(documents)
    chunks_with_embedding = embedding_chunks(docs)

    vector_store(chunks_with_embedding,table_name)

    create_HNSW_index(table_name)

    GIN_index(table_name)
    

# loading_chunking_embedding_storing(documents, TABLE_NAME)

