import os
from langchain_community.document_loaders import PyMuPDFLoader
from fastmcp import FastMCP
import io
import contextlib


mcp = FastMCP(name = "File System")


@mcp.tool
def list_files(path: str) -> list:

    """Return files available"""
    files = os.listdir(path)

    if not files:

        return "Your directory is empty kindly add some documents in it"

    return files



@mcp.tool
def doc_filter(files: list[str]) -> list:

    """Filtering pdf documents from the directory"""

    pdf = []
    for doc in files:
        if doc.endswith(".pdf"):
            pdf.append(doc)

    return pdf


@mcp.tool
def load_docs(path: str, pdf_docs : list[str] = None) -> list:

    """Loading all the pdf documents separately to isolate their metadata"""

    if pdf_docs:

        
        pdf_docs_object = []
        for document in pdf_docs:
            doc_path =  os.path.join(path, document)
            loader = PyMuPDFLoader(
                file_path=doc_path,
                extract_images=True,
                extract_tables='markdown')

            # PyMuPDF sometimes prints diagnostic hints to stdout, which
            # corrupts the JSON-RPC stdio stream this MCP server runs on.
            # Swallow anything it writes here.
            with contextlib.redirect_stdout(io.StringIO()):
                docs = loader.load()
                
            pdf_docs_object.append(docs)

        return pdf_docs_object

    return []


if __name__ == '__main__':

    mcp.run()