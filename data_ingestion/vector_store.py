from data_ingestion.doc_splitter import chunks_of_docs
from data_ingestion.embedding_generation import embedding_chunks
from config.config import db_connection, DB_CONNECTION_URL
from psycopg2 import sql
from psycopg2.extras import Json


conn, cursor = db_connection(DB_CONNECTION_URL)


def clean_text(value):
    if isinstance(value, str):
        return value.replace('\x00', '')
    return value


def vector_store(chunks_with_embedding : list, table_name: str):


    try:

        for chunk in chunks_with_embedding:

            embdding = chunk['embeddings']
            page_content = clean_text(chunk['page_content'])
            metadata = chunk['metadata']
            page_number = chunk['metadata']['page']
            document_name = chunk['metadata']['source'].split("/")[-1]

            cursor.execute(sql.SQL("""
            INSERT INTO {}(
            embeddings,
            page_content,
            metadata,
            page_number,
            document_name
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
        print("Data Inserted successfully")

    except Exception as e:
        raise ValueError(f"Can't able to store embeddings and chunks into db due to \n Error Details : {e}")


