from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()




# =============================== LLM provider ===============================
def Gemini_model_provider():
    """
    Gemini model provider
    """
    try:
        model = ChatGoogleGenerativeAI(model = 'gemini-3.5-flash')
        return model
    except Exception as e:

        raise print(f"There might be some API key or token access reached it's maximum limit \n Further Details: {e}")



def listing_files_reasoning_model():

    """Groq model for listing files"""
    try:
        listing_load_model = ChatGroq(model="openai/gpt-oss-120b")
        return listing_load_model
    except Exception as e:
        raise print(f"There might be some API key or token access reached it's maximum limit \n Further Details: {e}")



def classifier_model():

    """
    Groq model (free to use)f to classify intent best for general purpose
    """
    try:
        classifier_model   = ChatGroq(model="openai/gpt-oss-20b")  
        return classifier_model
    except Exception as e:
            raise print(f"There might be some API key or token access reached it's maximum limit \n Further Details: {e}")





# =============================== DATABASE credentials & conection ===============================
# Database credential
USERNAME = os.getenv('USER_NAME')
PASSWORD = os.getenv('PASSWORD')
DB_NAME = 'rag_db'
TABLE_NAME = 'rag_docs'
POSTGRES_ADMIN_URL = os.getenv("POSTGRES_ADMIN_URL")
DB_CONNECTION_URL = os.getenv("POSTGRES_DB_URL_RAG_DB")

def db_connection(DB_URL):

    """Establishing connection with DB"""
    conn = psycopg2.connect(DB_URL)
    # to commit all the operations automatically========================
    conn.autocommit = True
    cursor = conn.cursor()

    return conn, cursor





# =============================== Tavily for websearch ===============================
TAVILY_WEBSEARCH = os.getenv("TAVILY_WEBSEARCH")





# =============================== Prompts ===============================
query_generator_prompt = """
You are a query expansion module for a RAG system.

Given the user's original query, generate exactly 2 alternative search queries.

Rules:
1. Preserve the exact intent of the original query.
2. Do not add information, assumptions, entities, or facts that are not present in the original query.
3. Rephrase the query using different wording, terminology, or sentence structure.
4. Keep important technical terms, names, and concepts unchanged when necessary.
5. Each alternative must be meaningfully different from the others.
6. Make every query concise and suitable for semantic and keyword retrieval.
7. Do not answer the user's question.
8. Do not provide explanations, numbering, bullets, or commentary.
9. Return only the alternative queries, one query per line.
"""


agent_tool_usage_instruction = """
You are a document discovery agent.

The user-authorized folder path will be provided in the user context.

IMPORTANT:
- Always use the provided authorized folder path when calling filesystem tools.
- Never use your current working directory.
- Never invent or change the folder path.

You have access to exactly two tools:

1. `list_files(path)` — lists all files in the user's authorized directory.
2. `doc_filter(files)` — filters a file list down to PDF files.

Follow these rules:

* If the user asks to list/show all files, call `list_files` and return the files. Do not call `doc_filter`.
* If the user asks to show/list/count PDF documents, call `list_files`, then `doc_filter`, and return the PDFs.
* If the user asks whether a particular file exists, call `list_files` and check the result.
* If the user asks to load documents:
  1. Call `list_files`.
  2. Call `doc_filter`.
  3. Determine which PDF files match the user's request.
  4. Tell the user which PDFs are available for loading and ask them to confirm or select which ones.
* You cannot load documents yourself — loading is handled by a separate step once the user confirms. Never claim to have loaded anything.
* If the user gives an approximate or misspelled filename, match it against the available PDF filenames and mention the closest reasonable match when asking for confirmation.

Your job ends once you've either answered a listing/counting question directly, or asked the user which PDFs to load. You never load files yourself.
"""


load_docs_agent_prompt = """
You are a document loading agent.
...

Your final result must have this structure:

{{
    "loaded_documents": List[Document],
    "document_names": List[str]
}}

The document_names must contain the exact filenames selected by the user.

Example:

AVAILABLE DOCUMENTS:
1. RoPE.pdf
2. CME295_Transformers_Refined_Notes.pdf
3. MCP_Refined_Notes.pdf

USER CONFIRMATION:
"No, just load the first one."

Call:

load_docs(["RoPE.pdf"])

Then return:

{{
    "loaded_documents": [the Document object returned by load_docs],
    "document_names": ["RoPE.pdf"]
}}

Another example:
...

Return:

{{
    "loaded_documents": [the returned Document objects],
    "document_names": [
        "RoPE.pdf",
        "MCP_Refined_Notes.pdf"
    ]
}}
"""



intent_classifier_prompt = ChatPromptTemplate.from_messages([
        ('system',"""You are an intent classifier for an AI system with two main capabilities: **document management** and **RAG-based question answering**.

            Your ONLY task is to classify the user's query into exactly ONE of these two intents:

            * **document** — The user wants to interact with, inspect, list, count, select, load, or manage files/documents in their document folder.
            * **RAG** — The user wants information, an explanation, an answer, or a search based on the content of documents already available to the RAG system.

            ### Examples

            * "How many documents do I have?" → document
            * "Show me all my files." → document
            * "What PDFs are in my folder?" → document
            * "List my documents." → document
            * "Load all the documents." → document
            * "Load RoPE.pdf." → document
            * "I want to load my transformer notes." → document
            * "Which documents do I have about transformers?" → document
            * "What is RoPE?" → RAG
            * "Explain rotary positional embeddings." → RAG
            * "What does the transformer paper say about attention?" → RAG
            * "Summarize my transformer notes." → RAG
            * "According to my documents, what is self-attention?" → RAG
            * "Compare the information in my two transformer documents." → RAG
            * "What is the latest research on transformers?" → RAG
            * "Hello" → RAG
            * "How many files/PDFs do I have?" → document, list
            * "Show me my PDFs" → document, list
            * "Load all the docs" → document, load
            * "Load RoPE.pdf" → document, load

            * `document`
            * `RAG`
            """),
        ('human',"Query: {query}")
])
