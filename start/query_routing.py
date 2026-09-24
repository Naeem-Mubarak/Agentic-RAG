from graph.states.states import Agent_state
from typing import Literal
import os


def query_router(state: Agent_state) -> Literal['File_System_MCP','retriever','no_path_found']:


    """
    route query based on the intent if user wants to perform action with documents then check is the path valid if it is then go to file system mcp client to establish connection with server otherwise go to no file found.
    if the query intent is RAG then go to retriever
    """

    if state['intent'] == 'document':
        path = state['folder_path']


        # file path checking 
        if not path: 
            return 'no_path_found'

        if not os.path.isdir(path):
            return 'no_path_found'

        try:
            os.listdir(path)

        except PermissionError:

            return "no_path_found"

        return 'File_System_MCP'

    return 'retriever'