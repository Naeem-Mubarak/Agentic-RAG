import os
from langchain_community.document_loaders import PyMuPDFLoader
from fastmcp import FastMCP
import io
import json
import contextlib
from typing import Optional


mcp = FastMCP(name = "File System")


@mcp.tool
def list_files(path: str) -> str:
    """Return all files available, including those inside subfolders."""
    if not path or not os.path.isdir(path):
        return json.dumps([])

    all_files = []
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, path)
                all_files.append(rel_path)
    except PermissionError:
        return json.dumps([])

    return json.dumps(all_files)




@mcp.tool
def doc_filter(files: list[str], folder: Optional[str] = None):

    """Filtering pdf documents from the directory"""

    pdf = []
    for doc in files:
        if not doc.lower().endswith(".pdf"):
            continue

        if folder:
            doc_folder = os.path.dirname(doc)
            target = folder.strip().lower()
            if not (doc_folder.lower() == target or doc_folder.lower().startswith(target + os.sep)):
                continue

        pdf.append(doc)

    return json.dumps(pdf)




@mcp.tool
def load_docs(path: str, pdf_docs: list[str] = None) -> str:
    """Loading all the pdf documents separately to isolate their metadata"""

    if not pdf_docs:
        return json.dumps({"documents": [], "errors": []})

    pdf_docs_object = []
    errors = []

    for document in pdf_docs:
        doc_path = os.path.join(path, document)

        if not os.path.isfile(doc_path):
            errors.append({"file": document, "error": "File not found on disk"})
            continue

        try:
            loader = PyMuPDFLoader(
                file_path=doc_path,
                # extract_images=True,
                extract_tables='markdown'
            )
            with contextlib.redirect_stdout(io.StringIO()):
                docs = loader.load()

            # Convert to plain dicts explicitly — never rely on default
            # serialization of LangChain Document objects across the MCP boundary.
            serialisable_docs = [
                {"page_content": d.page_content, "metadata": d.metadata}
                for d in docs
            ]
            pdf_docs_object.append(serialisable_docs)

        except Exception as e:
            errors.append({"file": document, "error": str(e)})
            continue

    return json.dumps({"documents": pdf_docs_object, "errors": errors})


if __name__ == '__main__':

    mcp.run()