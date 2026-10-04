from backend.config.config import db_connection, DB_CONNECTION_URL
from psycopg2 import sql
from psycopg2.extras import Json


conn, cursor = db_connection(DB_CONNECTION_URL)


def clean_text(value):

    """
    Postgre has some issues while saving some specifc type of messy data 
    so this functino cleans the data
    """
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value



def vector_store(chunks_with_embedding : list, table_name: str):

    """
    Storing chunks of emebddings with it's metadata source and page_number
    in postgres DB
    """

    try:

        for chunk in chunks_with_embedding:

            embdding = chunk['embeddings']
            page_content = clean_text(chunk['page_content'])
            metadata = chunk['metadata']
            page_number = chunk['metadata']['page']
            document_name = chunk['metadata']['source'].split("/")[-1]

            cursor.execute(sql.SQL(""" INSERT INTO {}(
            embeddings, page_content, metadata, page_number, document_name
            )
            VALUES (%s,%s,%s,%s,%s)
            """).format(sql.Identifier(table_name)),
            (
                embdding.tolist(), 
                page_content, 
                Json(metadata), 
                page_number, 
                document_name
            )

            )


    except Exception as e:
        raise ValueError(f"Can't able to store embeddings and chunks into db due to \n Error Details : {e}")


