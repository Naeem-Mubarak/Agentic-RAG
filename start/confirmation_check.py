from config.config import confirmation_check_prompt, general_model
from pydantic import BaseModel


# schema defining
class confirmation_response(BaseModel):

    is_confirmation: bool


# model to classify
model = general_model()


def is_confirmation(pending_question: str, user_message: str) -> bool:
    """
    Decide whether the user's new message is answering the pending
    confirmation question (e.g. "yes", "the first one", "none"), or is an
    unrelated request / topic change that should abandon the interrupted
    flow and start a fresh graph run instead.
    """

    structured_llm = model.with_structured_output(confirmation_response)

    chain = confirmation_check_prompt | structured_llm

    response = chain.invoke({
        "pending_question": pending_question,
        "user_message": user_message
    })

    return response.is_confirmation
