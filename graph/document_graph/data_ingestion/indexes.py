from psycopg2 import sql
from config.config import DB_CONNECTION_URL, db_connection, TABLE_NAME



conn, cursor = db_connection(DB_CONNECTION_URL)


def create_HNSW_index(table_name: str = TABLE_NAME):

    """Creating HNSW index for fast search"""

    try: 
        cursor.execute(
        sql.SQL("""
                CREATE INDEX IF NOT EXISTS 
                rag_docs_embeddings_hnsw_idx 
                ON {}
                USING hnsw (embeddings vector_cosine_ops)
                """).format(sql.Identifier(table_name)
            )
        )

        print("HNSW index created succesfully")

    except Exception as e:
        raise ValueError(f"Some unexpected error occured during HNSW index creation \n Error Details: {e}")




def GIN_index(table_name: str  = TABLE_NAME):

    try:

        cursor.execute(
            sql.SQL("""CREATE INDEX IF NOT EXISTS
            rag_docs_content_tsv_idx
            ON {}
            USING GIN (content_tsv)
            """).format(sql.Identifier(table_name))
        )

        print("GIN index created succesfully")

    except Exception as e:

        raise ValueError(f"Some Unknown error occured during creating GIN index for keyword search \n Error Details: {e}")
