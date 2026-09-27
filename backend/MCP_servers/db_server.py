import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


from fastmcp import FastMCP
from backend.config.config import TABLE_NAME
from psycopg2 import sql
from backend.config.config import db_connection,DB_CONNECTION_URL
import json




mcp = FastMCP(name = "db_server")


@mcp.tool
def docs_in_db(table_name : str = TABLE_NAME):

    """
    List all the tools preent in Database
    """

    try:
       
        conn, cursor = db_connection(DB_CONNECTION_URL)
        cursor.execute(
                    sql.SQL("""SELECT DISTINCT document_name FROM {}""").format(
                        sql.Identifier(table_name)
                    )
                )
        data = cursor.fetchall()
        docs_name = [doc_name[0] for doc_name in data]

        return json.dumps({
            "documents": docs_name,
            "count": len(docs_name)
        })
        

    except Exception as e:
        raise ValueError(f"Some unknown error occured during getting document name from db \n Error Details: {e}")

    finally:

        cursor.close()
        conn.close()





@mcp.tool
def search_docs(docs_name : list[str], table_name : str = TABLE_NAME):

    """
    Search for provided docs that are they stored in DB or not
    """

    try:
        conn, cursor = db_connection(DB_CONNECTION_URL)
        cursor.execute(
                    sql.SQL("""SELECT DISTINCT document_name FROM {}""").format(
                        sql.Identifier(table_name)
                    )
                )
        data = cursor.fetchall()
        db_docs = [doc_name[0] for doc_name in data]
    
        present_docs = [doc for doc in docs_name if doc in db_docs]
        missing_docs = [doc for doc in docs_name if doc not in db_docs]
    
        return json.dumps({
            "present": present_docs,
            "missing": missing_docs
        })


    except Exception as e:
            raise ValueError(f"Some unknown error occured during getting document name from db \n Error Details: {e}")
    
    finally:
    
        cursor.close()
        conn.close() 





@mcp.tool
def delete_docs(docs_name: list[str], table_name: str = TABLE_NAME):

    """
    Delete provided document from the databse
    """

    try:
        conn, cursor = db_connection(DB_CONNECTION_URL)

        for doc in docs_name:
            cursor.execute(
                sql.SQL("""
                    DELETE FROM {} 
                    WHERE document_name = %s
                """).format(
                    sql.Identifier(table_name)
                ),
                (doc,)
            )

        return json.dumps({
            "deleted": docs_name
        })
    
    except Exception as e:
        raise ValueError(f"Some unknown error occured during getting document name from db \n Error Details: {e}")
        
    finally:
        
        cursor.close()
        conn.close() 


if __name__ == '__main__':

    mcp.run()