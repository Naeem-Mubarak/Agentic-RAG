from backend.config.config import db_connection, DB_CONNECTION_URL, TABLE_NAME
from psycopg2 import sql


def keyword_search(query: str, table_name :str = TABLE_NAME,top_k: int = 5):

    """
    Retreiving documents on the basis of keyword search
    """

    conn, cursor = db_connection(DB_CONNECTION_URL)

    try:

        cursor.execute(
            sql.SQL("""SELECT
            id,
            page_content,
            metadata,
            page_number,
            document_name,
            ts_rank(
                content_tsv,
                plainto_tsquery('english', %s)
            ) AS score
        FROM {}
        WHERE content_tsv @@ plainto_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT %s;
        """).format(sql.Identifier(table_name)),
        (query, query, top_k)
        )

        results = cursor.fetchall()

        print("Key word search is done")

        return results

    except Exception as e:
        raise ValueError(f"Some unexpected error occured druing keyword search \n Error Details: {e}")

    finally:
        cursor.close()
        conn.close()