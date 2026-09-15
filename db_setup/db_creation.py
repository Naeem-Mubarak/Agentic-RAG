from dotenv import load_dotenv
from config.config import username, password, DB_NAME, POSTGRES_ADMIN_URL , db_connection



# Database connection
conn, cursor = db_connection(POSTGRES_ADMIN_URL)


def database_creation(username: str, password: str, DB_NAME: str):


    """Database creation and assigning user to the database and making him owner"""

    if not username:
        raise ValueError("Username can't be empty")
    if not password:
        raise ValueError("please set your password")
    if not DB_NAME:
        raise ValueError("You didn't provide the db name")


    try:

        # creating user
        cursor.execute(f"CREATE USER {username} WITH PASSWORD %s",(password,))
        print("User created")

        # creating database and giving full access
        cursor.execute(f"CREATE DATABASE {DB_NAME} OWNER {username}")
        print(f"database created and owned by {username}")

    except Exception as e:
        raise ValueError(f"Some error occured during database creation and assigning user \n Error Details: {e}")


    cursor.close()
    conn.close()


database_creation(username,password,DB_NAME)