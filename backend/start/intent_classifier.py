from backend.config.config import intent_classifier_prompt,general_model
from backend.graph.states.states import Agent_state
from pydantic import BaseModel
from typing import Literal


# schema defining
class user_intent(BaseModel):

    intent : Literal["document","RAG", "DB","general"]
    document_action: Literal["list", "load", "none"] = "none"


# model to classify intent
model = general_model()


def intent_classifier(state: Agent_state):

    """
    Classify the intent of the user that wether he wants to perform some document action or he wants to ask some query from his documetns.
    Two intents
    1. document
    2. RAG
    it also calssify in case of document that what action user want's to perform laod (in DB) or list files
    """

    # enforcing schema
    structured_llm = model.with_structured_output(user_intent)

    chain = intent_classifier_prompt | structured_llm

    response = chain.invoke({
        "query" : state['query']
    })


    # state updation
    state['intent'] = response.intent
    state['document_action'] = response.document_action

    return state
