from langchain_text_splitters import RecursiveCharacterTextSplitter



def chunks_of_docs(docs) -> list:

    """
    creating chunks of the documents using recursive charachter splitter.
    """

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

    print("Chunks are generated successfully")

    return combine_chunks