from langgraph.graph import END,StateGraph,START
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import MemorySaver
from backend.agent.start.intent_classifier import intent_classifier
from backend.agent.start.query_routing import query_router
from backend.agent.states.states import Agent_state
from backend.agent.fallback.file_not_found import no_path_found
from backend.rag.refinement.document_classification import document_classification
from backend.rag.refinement.knowledge_refinement import knoweldge_refinement
from backend.rag.generation.ambiguous import ambiguis
from backend.rag.generation.doc_class_router import doc_class_router
from backend.rag.generation.irrelevant import irrelvent
from backend.rag.generation.relevant import relevent
from backend.rag.retrieval.retriever_evaluator import retriever_evaluator
from backend.rag.retrieval.retriever_node import retriever
from backend.mcp.clients.websearch_client import web_search
from backend.mcp.clients.filesystem_client import File_System_MCP
from backend.documents.graph.load_docs import load_docs
from backend.documents.graph.document_ingestion import ingest_documents
from backend.mcp.clients.db_client import DB_mcp
from backend.rag.generation.no_retrieval import no_search_response_generator



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