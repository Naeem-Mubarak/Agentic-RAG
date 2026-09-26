from backend.config.config import db_connection, DB_CONNECTION_URL, POSTGRES_ADMIN_URL, DB_NAME
from psycopg2 import sql
from urllib.parse import urlparse, urlunparse


def table_creation(table_name: str, DB_NAME : str = DB_NAME):

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

    # admin connection required to activate extension so giving the right url including db_name where to activate extension
    parsed = urlparse(POSTGRES_ADMIN_URL)
    admin_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        f"/{DB_NAME}",
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


    admin_conn , admin_cursor = db_connection(admin_url)
    try:

        admin_cursor.execute("""CREATE EXTENSION IF NOT EXISTS vector""")
        print("vector extension activated")

    except Exception as e:

        raise ValueError(f"Some unexpected error occured during extension activation \n Error Detail : {e}")

    finally:

        admin_conn.close()
        admin_cursor.close()

    # user connection for creating table in it's DB
    conn, cursor = db_connection(DB_CONNECTION_URL)

    try:

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}(
            id BIGSERIAL PRIMARY KEY,
            embeddings vector(2000) NOT NULL,
            page_content TEXT NOT NULL,
            metadata JSONB,
            page_number INTEGER,
            document_name TEXT NOT NULL,
            content_tsv tsvector
                GENERATED ALWAYS AS (
                to_tsvector('english', page_content)
                ) STORED
            )
        """).format(sql.Identifier(table_name)))

        print(f"Table: {table_name} created successfully") 
    
    except Exception as e:
        raise ValueError(f"Some Error is occured during table creation \n Error Details: {e}")

    finally:

        cursor.close()
        conn.close()
