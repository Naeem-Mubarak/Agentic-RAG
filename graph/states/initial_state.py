
def build_initial_state(query: str, folder_path: str) -> dict:
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
        "final_answer": ""
    }


# Kept for main.py's simple single-threaded CLI testing script —
# do not reuse this shared dict anywhere concurrent (see build_initial_state above).
initial_state = {
    "folder_path": '/home/naeemmubarak/Desktop/Books',
    "intent": None,
    "document_action": "none",
    "query": "",
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
    "final_answer": ""
}