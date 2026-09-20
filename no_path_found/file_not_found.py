from states.states import subgraph_state

def no_path_found(state: subgraph_state):

    state['tool_response'] = "I don't have access to any of your folder kindly give access to folders"

    return state