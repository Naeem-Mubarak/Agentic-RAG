from backend.config.config import db_connection, DB_CONNECTION_URL
from psycopg2 import sql



def chat_saving_tables(table_name1: str, table_name2 : str):

    """Table to store chat data in the database 
    ============= chat table =============
    1. thread_id : unique id
    2. title : tile of chat (we can see in side bar)
    3. created_at : time at which chat is created

    ============= chat history table =============
    1. id : unique id
    2. thread_id : (foreign key)
    3. query : question from user (dtype is JSONB because we want to store it as Human message)
    4. response : response from agent (dtype is JSONB because we want to store it as AI message)
    5. created_at : time at which chat is created
    """

    if table_name1 == table_name2:
        return "Provide different table name to avoid confusion"
    
    # user connection for creating table in it's DB
    conn, cursor = db_connection(DB_CONNECTION_URL)

    try:

        cursor.execute(sql.SQL("""
            CREATE TABLE {} (
                thread_id   TEXT PRIMARY KEY,
                title       TEXT,
                created_at  TIMESTAMPTZ DEFAULT now()
            );
            CREATE TABLE {} (
                id          SERIAL PRIMARY KEY,
                thread_id   TEXT NOT NULL REFERENCES {}(thread_id) ON DELETE CASCADE,
                query       JSONB Not null,
                response    JSONB,
                created_at  TIMESTAMPTZ DEFAULT now()
            );
        """).format(
            sql.Identifier(table_name1),
            sql.Identifier(table_name2),    
            sql.Identifier(table_name1)
        ))

        print(f"Tables: {table_name1} {table_name2} for chat history maintaince are created successfully") 
    
    except Exception as e:
        raise ValueError(f"Some Error is occured during table creation \n Error Details: {e}")

    finally:

        cursor.close()
        conn.close()