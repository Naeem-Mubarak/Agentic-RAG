from backend.documents.ingestion.splitter import chunks_of_docs
from backend.documents.ingestion.embeddings import embedding_chunks
from backend.documents.ingestion.vector_store import vector_store
from backend.documents.ingestion.indexes import create_HNSW_index, GIN_index
from backend.config.config import TABLE_NAME



def loading_chunking_embedding_storing(documents: list, table_name: str = TABLE_NAME) -> None:

    """
    data ingestion pipeline doing all the stuff loading chunking emebddnig generatino and also storing them in DB and creating index for fast search (HNSW) and for key word search (GIN)
    """

    docs = chunks_of_docs(documents)
    chunks_with_embedding = embedding_chunks(docs)

    vector_store(chunks_with_embedding,table_name)

    create_HNSW_index(table_name)

    GIN_index(table_name)
    


