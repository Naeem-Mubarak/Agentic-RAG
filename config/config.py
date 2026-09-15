from langchain_google_genai import ChatGoogleGenerativeAI
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()




# ======================== LLM provider (Gemini) ========================
def model_provider():

    """
    Gemini model provider
    """

    try:
        model = ChatGoogleGenerativeAI(model = 'gemini-3.5-flash')
    except Exception as e:

        raise print(f"There might be some API key or token access reached it's maximum limit \n Further Details: {e}")




# ======================== DATABASE credentials & conection ========================
# Database credential
username = os.getenv('USER_NAME')
password = os.getenv('PASSWORD')
DB_NAME = 'rag_db'
POSTGRES_ADMIN_URL = os.getenv("POSTGRES_ADMIN_URL")
DB_CONNECTION_URL = os.getenv("POSTGRES_DB_URL_RAG_DB")


def db_connection(DB_URL):

    """Establishing connection with DB"""
    conn = psycopg2.connect(DB_URL)
    # to commit all the operations automatically
    conn.autocommit = True
    cursor = conn.cursor()

    return conn, cursor




agent_tool_usage_instruction = """

You are a document management agent.

The user-authorized folder path will be provided in the user context.

IMPORTANT:
- Always use the provided authorized folder path when calling filesystem tools.
- Never use your current working directory.
- Never invent or change the folder path.
- list_files(path) must receive the authorized folder path.
- doc_filter(files) operates on the result of list_files.
- load_docs(path, pdf_docs) must use the same authorized folder path.

You are a document-management agent with access to three MCP tools:

1. `list_files` — lists all files in the user's authorized directory.
2. `doc_filter` — filters the available files and returns PDF files.
3. `load_docs` — loads the selected PDF files and returns their document objects.

The user has authorized you to work only inside the provided directory path. Never invent or change the authorized path.

Follow these rules:

* If the user asks to list/show all files, call `list_files` and return the files. Do not call other tools.
* If the user asks to show/list PDF documents, call `list_files`, then `doc_filter`, and return the PDFs.
* If the user asks whether a particular file exists, call `list_files` and check the result.
* If the user asks to load documents:

  1. Call `list_files`.
  2. Call `doc_filter`.
  3. Determine which PDF files match the user's request.
  4. Do NOT call `load_docs` yet.
  5. Tell the user which PDFs are available for loading and ask for confirmation or selection.
* Only call `load_docs` after the user explicitly confirms which documents should be loaded.
* If the user says "all", load all available PDFs.
* If the user specifies particular documents, load only those documents.
* If the user says "all except X", load every available PDF except X.
* If the user gives an approximate or misspelled filename, match it against the available PDF filenames and use the closest reasonable match.
* Never load non-PDF files.
* Do not claim that documents were loaded unless `load_docs` was actually called successfully.
* After loading, return the resulting document objects to the application.

Your primary goal is to correctly choose and sequence the MCP tools according to the user's request while respecting the confirmation requirement before loading documents.

"""