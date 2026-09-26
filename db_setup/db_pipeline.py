from db_setup.db_creation import database_creation
from db_setup.table_creation import table_creation
from backend.config.config import USERNAME, PASSWORD, DB_NAME, TABLE_NAME, Chat_table_main, Complete_Chat_table
from db_setup.chat_history_tables.table_creation_for_chat import chat_saving_tables



def db_pipeline(username: str, password: str, DB_NAME: str, table_name: str, table_name_chat1: str , table_name_chat2: str) -> None:

    """
    Creating Database, user with password and then assigning authorities to the user and then creating table
    """

    database_creation(username,password,DB_NAME)

    table_creation(table_name, DB_NAME)

    chat_saving_tables(table_name_chat1, table_name_chat2)


db_pipeline(USERNAME, PASSWORD, DB_NAME, TABLE_NAME, Chat_table_main, Complete_Chat_table)

