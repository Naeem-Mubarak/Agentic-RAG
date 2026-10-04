from backend.agent.states.states import Agent_state

def no_path_found(state: Agent_state):

    state['tool_response'] = (
        f"The folder path '{state['folder_path']}' doesn't exist or isn't accessible. "
        "Please check the path and try again."
    )

    return state