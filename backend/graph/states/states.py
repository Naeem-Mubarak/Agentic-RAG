from typing import Literal,List,TypedDict
from langchain_core.documents import Document
from langchain.messages import AIMessage, HumanMessage


class Agent_state(TypedDict):

    folder_path : str

    intent : Literal["document","RAG","DB","general"]
    query : str

    document_action: Literal["list", "load", "none"] = "none"
    available_files : List[str]
    pdf_files : List[str]
    selected_docs : List[str]
    tool_response : str
    doc_obj : List[Document]


    retrieved_docs : List[dict]
    retrieval_score : List[float]
    doc_class : str
    
    filtered_knowledge : List[str]
    filtered_web_knowledge: List[str]  


    web_sources : List[dict]
    websearch : List[dict]

    message_history : str

    final_answer : str

    