from config.config import intent_classifier_prompt
from states.states import subgraph_state,user_intent
from config.config import classifier_model


def intent_classifier(state: subgraph_state):


    structured_llm = classifier_model.with_structured_output(user_intent)

    chain = intent_classifier_prompt | structured_llm

    response = chain.invoke({
        "query" : state['query']
    })

    state['intent'] = response.intent
    state['document_action'] = response.document_action

    return state
