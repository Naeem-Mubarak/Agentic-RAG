
def build_initial_state(query: str, folder_path: str = None, history: str = "") -> dict:
    """
    Fresh state dict per request. Never reuse a shared/module-level state
    object across concurrent connections -- nodes mutate state in place,
    so a shared dict would let two users corrupt each other's data.

    history: a plain formatted transcript string of this chat's earlier
    turns ("User: ...\nAssistant: ..."), used by the generation nodes to
    disambiguate follow-up questions. Empty string for a brand new chat.
    """
    return {
        "folder_path": folder_path,
        "intent": None,
        "document_action": "none",
        "query": query,
        "is_follow_up" : True,
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
        "message_history": history or "",
        "final_answer": ""
    }