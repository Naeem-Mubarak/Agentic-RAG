from config.config import db_connection, DB_CONNECTION_URL
from psycopg2 import sql

conn, cursor = db_connection(DB_CONNECTION_URL)


def table_creation(table_name: str):

    """Table to store data in the database
    1. ID : unique id
    2. embeddings : embedding vector of shape 1024 (Qwen 0.6B) (of corresponding chunk)
    3. page_content : chunk
    4. metadata : metadata of that chunk
    5. page_number : page number from which chunk extracted (source of chunk)
    6. document_name : name of the document to identify it clearly (source of chunk)
    """

    if not table_name:
        raise ValueError("Provide the name of your table")

    try:

        cursor.execute(sql.SQL("""
            CREATE TABLE {}(
            id BIGSERIAL PRIMARY KEY,
            embeddings vector(4096) NOT NULL,
            page_content TEXT NOT NULL,
            metadata JSONB,
            page_number INTEGER,
            document_name TEXT NOT NULL
            )
        """).format(sql.Identifier(table_name)))

        print(f"Table: {table_name} created successfully") 
    
    except Exception as e:
        raise ValueError(f"Some Error is occured during table creation \n Error Details: {e}")



table_creation("RAG_docs")