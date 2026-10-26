import re

from backend.config.config import confirmation_check_prompt, general_model
from pydantic import BaseModel


# schema defining
class confirmation_response(BaseModel):

    is_confirmation: bool


# model to classify
model = general_model()


_FIRST_WORD_CONFIRMATIONS = (
    "yes", "yeah", "yep", "yup", "confirm", "confirmed", "sure", "ok", "okay", "load"
)

_SUBSTRING_CONFIRMATIONS = (
    "confirm", "load it", "proceed", "go ahead", "start loading", "that's right", "that is right"
)


def _looks_like_obvious_confirmation(user_message: str) -> bool:
    """
    Fast, deterministic short-circuit for the overwhelming common case of a
    confirmation reply ("yes", "load it", "confirmed", "load the document i
    told you", etc.) -- this removes the LLM entirely from the highest-stakes,
    most frequent path, so it can never misjudge the obvious case. Only
    genuinely ambiguous messages fall through to the LLM-based check below.
    """
    normalized = re.sub(r"[^\w\s]", "", user_message.strip().lower())
    words = normalized.split()

    if not words:
        return False

    if words[0] in _FIRST_WORD_CONFIRMATIONS:
        return True

    if any(phrase in normalized for phrase in _SUBSTRING_CONFIRMATIONS):
        return True

    return False


def is_confirmation(pending_question: str, user_message: str) -> bool:
    """
    Decide whether the user's new message is answering the pending
    confirmation question (e.g. "yes", "the first one", "none"), or is an
    unrelated request / topic change that should abandon the interrupted
    flow and start a fresh graph run instead.
    """

    if _looks_like_obvious_confirmation(user_message):
        return True

    structured_llm = model.with_structured_output(confirmation_response)

    chain = confirmation_check_prompt | structured_llm

    try:
        response = chain.invoke({
            "pending_question": pending_question,
            "user_message": user_message
        })
        print(
            f"[is_confirmation] pending='{pending_question[:60]}...' "
            f"user='{user_message}' -> {response.is_confirmation}"
        )
        return response.is_confirmation
    except Exception as e:
        print(f"[is_confirmation] LLM check failed, defaulting to False: {e}")
        return False
