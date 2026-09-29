from langgraph.graph import END,StateGraph,START
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import MemorySaver
from backend.start.intent_classifier import intent_classifier
from backend.start.query_routing import query_router
from backend.graph.states.states import Agent_state
from backend.graph.no_path_found.file_not_found import no_path_found
from backend.graph.RAG_graph.docs_refining.document_classification import document_classification
from backend.graph.RAG_graph.docs_refining.knowledge_refinement import knoweldge_refinement
from backend.graph.RAG_graph.response_generaton.ambiguis_docs import ambiguis
from backend.graph.RAG_graph.response_generaton.doc_class_router import doc_class_router
from backend.graph.RAG_graph.response_generaton.irrelevant_docs import irrelvent
from backend.graph.RAG_graph.response_generaton.relevent_doc import relevent
from backend.graph.RAG_graph.retriever.retriever_evaluator import retriever_evaluator
from backend.graph.RAG_graph.retriever.retriever_node import retriever
from backend.graph.RAG_graph.retriever.websearch_mcp_client import web_search
from backend.graph.document_graph.graph.file_system_mcp_client import File_System_MCP
from backend.graph.document_graph.graph.load_docs import load_docs
from backend.graph.document_graph.graph.document_ingestion import ingest_documents
from backend.graph.db_operation.db_mcp_client import DB_mcp
from backend.graph.RAG_graph.response_generaton.no_search_response import no_search_response_generator



agent_graph = StateGraph(Agent_state)

agent_graph.add_node('intent_classifier', intent_classifier)
agent_graph.add_node('retriever', retriever, destinations=('retriever_evaluator',))
agent_graph.add_node("DB_MCP",DB_mcp, destinations=(END,))
agent_graph.add_node('no_search_response', no_search_response_generator)
agent_graph.add_node('no_path_found', no_path_found)
agent_graph.add_node('File_System_MCP', File_System_MCP,
    destinations=('load_docs', END)
)
agent_graph.add_node('load_docs', load_docs)
agent_graph.add_node('data_ingestion', ingest_documents,
    destinations=(END,),
    retry_policy=RetryPolicy(max_attempts=3)
)
agent_graph.add_node('retriever_evaluator', retriever_evaluator, destinations=('doc_classification', 'websearch'))
agent_graph.add_node('doc_classification', document_classification)
agent_graph.add_node('websearch', web_search, destinations=('knoweldge_refinement',))
agent_graph.add_node('knoweldge_refinement', knoweldge_refinement,
    destinations=('relevant', 'not_relevant', 'ambiguis')
)
agent_graph.add_node('relevant', relevent)
agent_graph.add_node('not_relevant', irrelvent)
agent_graph.add_node('ambiguis', ambiguis)
agent_graph.add_edge(START, 'intent_classifier')
agent_graph.add_conditional_edges('intent_classifier', query_router)
agent_graph.add_conditional_edges('doc_classification', doc_class_router)
agent_graph.add_edge('no_path_found', END)
agent_graph.add_edge('DB_MCP', END)
agent_graph.add_edge('no_search_response', END)
agent_graph.add_edge('load_docs', 'data_ingestion')


checkpointer = MemorySaver()
graph = agent_graph.compile(checkpointer=checkpointer)