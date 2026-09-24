from langgraph.graph import END,StateGraph,START
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import MemorySaver
from start.intent_classifier import intent_classifier
from start.query_routing import query_router
from graph.states.states import Agent_state
from graph.no_path_found.file_not_found import no_path_found
from graph.RAG_graph.docs_refining.document_classification import document_classification
from graph.RAG_graph.docs_refining.knowledge_refinement import knoweldge_refinement
from graph.RAG_graph.response_generaton.ambiguis_docs import ambiguis
from graph.RAG_graph.response_generaton.doc_class_router import doc_class_router
from graph.RAG_graph.response_generaton.irrelevant_docs import irrelvent
from graph.RAG_graph.response_generaton.relevent_doc import relevent
from graph.RAG_graph.retriever.retriever_evaluator import retriever_evaluator
from graph.RAG_graph.retriever.retriever_node import retriever
from graph.RAG_graph.retriever.websearch_mcp_client import web_search
from graph.document_graph.graph.file_system_mcp_client import File_System_MCP
from graph.document_graph.graph.load_docs import load_docs
from graph.document_graph.graph.document_ingestion import ingest_documents



subgraph = StateGraph(Agent_state)

subgraph.add_node('intent_classifier', intent_classifier)
subgraph.add_node('retriever', retriever, destinations=('retriever_evaluator',))
subgraph.add_node('no_path_found', no_path_found)
subgraph.add_node('File_System_MCP', File_System_MCP,
    destinations=('load_docs', END)
)
subgraph.add_node('load_docs', load_docs)
subgraph.add_node('data_ingestion', ingest_documents,
    destinations=(END,),
    retry_policy=RetryPolicy(max_attempts=3)
)
subgraph.add_node('retriever_evaluator', retriever_evaluator, destinations=('doc_classification', 'websearch'))
subgraph.add_node('doc_classification', document_classification)
subgraph.add_node('websearch', web_search, destinations=('knoweldge_refinement',))
subgraph.add_node('knoweldge_refinement', knoweldge_refinement,
    destinations=('relevant', 'not_relevant', 'ambiguis')
)
subgraph.add_node('relevant', relevent)
subgraph.add_node('not_relevant', irrelvent)
subgraph.add_node('ambiguis', ambiguis)

subgraph.add_edge(START, 'intent_classifier')
subgraph.add_conditional_edges('intent_classifier', query_router)
subgraph.add_conditional_edges('doc_classification', doc_class_router)
subgraph.add_edge('no_path_found', END)
subgraph.add_edge('load_docs', 'data_ingestion')

checkpointer = MemorySaver()
graph = subgraph.compile(checkpointer=checkpointer)