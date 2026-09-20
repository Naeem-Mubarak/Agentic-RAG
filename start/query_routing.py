from states.states import subgraph_state
from typing import Literal



def query_router(state: subgraph_state) -> Literal['File_System_MCP','RAG','no_path_found']:

    if state['intent'] == 'document' and state['folder_path'] is None:

        return 'no_path_found'

    elif state['intent'] == 'document' and state['folder_path'] is not None:

        return 'File_System_MCP'

    return 'RAG'