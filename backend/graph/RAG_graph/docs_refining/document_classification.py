from backend.graph.states.states import Agent_state



def document_classification(state: Agent_state):

    low_val = 0.5
    high_val = 1.0
    filtered_numbers = [x for x in state['retrieval_score'] if low_val <= x <= high_val]

    if len(filtered_numbers)>2:
        state['doc_class'] = 'relevant'

    elif len(filtered_numbers) == 0:
        state['doc_class'] = 'irrelevant'

    else:
        state['doc_class'] = 'ambiguis'

    return state