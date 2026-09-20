from db_setup.db_creation import database_creation
from db_setup.table_creation import table_creation
from config.config import USERNAME, PASSWORD, DB_NAME, TABLE_NAME

def db_pipeline(username: str, password: str, DB_NAME: str, table_name: str) -> None:

    """
    Creating Database, user with password and then assigning authorities to the user and then creating table
    """

    database_creation(username,password,DB_NAME)

    table_creation(table_name, DB_NAME)


db_pipeline(USERNAME, PASSWORD, DB_NAME, TABLE_NAME)

