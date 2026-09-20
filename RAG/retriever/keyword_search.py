from config.config import db_connection, DB_CONNECTION_URL, TABLE_NAME
from psycopg2 import sql

conn, cursor = db_connection(DB_CONNECTION_URL)


def column_for_keyword_search(table_name: str= TABLE_NAME):

    try:

        cursor.execute(
            sql.SQL("""ALTER TABLE {}
            ADD COLUMN content_tsv tsvector
            GENERATED ALWAYS AS (
            to_tsvector('english', page_content)
            ) STORED;
            """).format(sql.Identifier(table_name))
        )

        print("Column: content_tsv added successfully in table: ",table_name)

    except Exception as e:

        raise ValueError(f"Some Unknown error occured during adding column for keyword search \n Error Details: {e}")

    finally:

        cursor.close()
        conn.close()




def keyword_search(query: str, table_name :str = TABLE_NAME,top_k: int = 5):

    conn, cursor = db_connection(DB_CONNECTION_URL)

    try:

        cursor.execute(
            sql.SQL("""SELECT
            id,
            page_content,
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

        return results

    except Exception as e:
        raise ValueError(f"Some unexpected error occured druing keyword search \n Error Details: {e}")

    finally:
        cursor.close()
        conn.close()