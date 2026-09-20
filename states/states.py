from pydantic import BaseModel
from typing import Literal,List,TypedDict
from langchain_core.documents import Document


class user_intent(BaseModel):

    intent : Literal["document","RAG"]
    document_action: Literal["list", "load", "none"] = "none"



class subgraph_state(TypedDict):

    folder_path : str

    intent : Literal["document","RAG"]
    query : str

    document_action: Literal["list", "load", "none"] = "none"
    available_files : List[str]
    pdf_files : List[str]
    selected_docs : List[str]
    tool_response : str
    doc_obj : List[Document]

    