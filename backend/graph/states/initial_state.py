
def build_initial_state(query: str, folder_path: str = None) -> dict:
    """
    Fresh state dict per request. Never reuse a shared/module-level state
    object across concurrent connections — nodes mutate state in place,
    so a shared dict would let two users corrupt each other's data.
    """
    return {
        "folder_path": folder_path,
        "intent": None,
        "document_action": "none",
        "query": query,
        "available_files": [],
        "pdf_files": [],
        "selected_docs": [],
        "tool_response": "",
        "doc_obj": [],
        "retrieved_docs": [],
        "retrieval_score": [],
        "doc_class": "",
        "filtered_knowledge": [],
        "filtered_web_knowledge": [],
        "web_sources": [],
        "websearch": [],
        "message_history": [],
        "final_answer": ""
    }