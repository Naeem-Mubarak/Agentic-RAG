from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader


loader1 = PyMuPDFLoader("RAG_documents/CME295_Transformers_Refined_Notes.pdf", extract_images=True, extract_tables="markdown")
loader2 = PyMuPDFLoader("RAG_documents/MCP_Refined_Notes.pdf")
loader3 = PyMuPDFLoader("RAG_documents/RoPE.pdf")

doc1 = loader1.load()
doc2 = loader2.load()
doc3 = loader3.load()

documents = [doc1, doc2]



def chunks_of_docs(docs) -> list:

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 20,
        length_function = len
    )

    # iterating over all the document objects and splitting them 
    splitted_docs = []
    for doc_obj in docs:
        splitted_docs.append(text_splitter.split_documents(doc_obj))

    # combining the chunks of all the documents 
    combine_chunks = [chunk for doc_chunk in splitted_docs for chunk in doc_chunk]

    return combine_chunks





# data = {'producer': 'xdvipdfmx (20220710)', 'creator': 'LaTeX via pandoc', 'creationdate': '2026-09-09T09:15:32+00:00', 'source': 'RAG_documents/CME295_Transformers_Refined_Notes.pdf', 'file_path': 'RAG_documents/CME295_Transformers_Refined_Notes.pdf', 'total_pages': 15, 'format': 'PDF 1.5', 'title': 'Transformers & LLMs — Refined Study Notes', 'author': 'Naeem', 'subject': '', 'keywords': '', 'moddate': '', 'trapped': '', 'modDate': '', 'creationDate': "D:20260909091532-00'00'", 'page': 0}
