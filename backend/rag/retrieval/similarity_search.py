from backend.config.config import db_connection, DB_CONNECTION_URL
from backend.documents.ingestion.embeddings import embedding_generation
from psycopg2 import sql
from backend.config.config import TABLE_NAME


    

def similarity_retreiver(query: str, TABLE_NAME: str = TABLE_NAME, top_k: int = 5):

    """
    Retrieving documents based on the similarity socre
    """

    query_embedding, model_used = embedding_generation(query)

    if model_used == 'gemini':

        query_embedding = query_embedding.embeddings[0].values

    query_embedding = query_embedding.flatten().tolist()

    conn, cursor = db_connection(DB_CONNECTION_URL)

    cursor.execute(
        sql.SQL("""SELECT
        id,
        page_content,
        metadata,
        page_number,
        document_name,
        1 - (embeddings <=> %s::vector) AS similarity
        FROM {}
        ORDER BY embeddings <=> %s::vector
        LIMIT %s
        """).format(
            sql.Identifier(TABLE_NAME)
        ),(
            query_embedding,
            query_embedding,
            top_k,
        )
    )

    results = cursor.fetchall()

    cursor.close()
    conn.close()


    print("Similarity Search is done")

    return results


