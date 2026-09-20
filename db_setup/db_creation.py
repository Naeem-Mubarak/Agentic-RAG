from dotenv import load_dotenv
from config.config import POSTGRES_ADMIN_URL , db_connection
from psycopg2 import sql


# Database connection
conn, cursor = db_connection(POSTGRES_ADMIN_URL)


def database_creation(USERNAME: str, PASSWORD: str, DB_NAME: str):


    """Database creation and assigning user to the database and making him owner"""

    if not USERNAME:
        raise ValueError("Username can't be empty")
    if not PASSWORD:
        raise ValueError("please set your password")
    if not DB_NAME:
        raise ValueError("You didn't provide the db name")


    try:

        # creating user
        cursor.execute(
            sql.SQL("""CREATE USER {} WITH PASSWORD %s""").format(
                sql.Identifier(USERNAME)
            ),
            (PASSWORD,)
        )
        print("User created")

        # creating database and giving full access
        cursor.execute(
            sql.SQL("""CREATE DATABASE {} OWNER {}""").format(
                sql.Identifier(DB_NAME),
                sql.Identifier(USERNAME)
            )
        )
        print(f"database created and owned by {USERNAME}")

    except Exception as e:
        raise ValueError(f"Some error occured during database creation and assigning user \n Error Details: {e}")

    finally:

        cursor.close()
        conn.close()