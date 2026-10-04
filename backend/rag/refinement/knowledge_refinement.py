from pydantic import BaseModel
from typing import List,Literal
from backend.agent.states.states import Agent_state
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command
from backend.config.config import knowledge_filter_prompt, general_model
import re

model = general_model()


class filtered_knowledge(BaseModel):

    useful_sentence : List[int]



def decompose_strips(text: str) -> list[str]:
    """
    Split paragraph into sentences.
    """
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)

    return [
        s.strip()
        for s in sentences
        if len(s.strip()) > 20
    ]




def _refine(query: str, docs: list[dict]) -> list[dict]:

    sentences = []

    for doc_idx, doc in enumerate(docs):

        doc_sentences = decompose_strips(doc["content"])

        for sentence in doc_sentences:
            sentences.append({
                "id": len(sentences),
                "text": sentence,
                "source": doc["source"],
                "page_number": doc["page_number"],
                "metadata": doc["metadata"],
            })

    sentence_text = "\n".join(
        f"[{sentence['id']}] {sentence['text']}"
        for sentence in sentences
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", knowledge_filter_prompt),
        (
            "human",
            "Query: {query}\n\n"
            "Candidate sentences:\n{sentences}"
        )
    ])

    structured_llm = model.with_structured_output(filtered_knowledge)

    chain = prompt | structured_llm

    response = chain.invoke({
        "query": query,
        "sentences": sentence_text
    })

    selected_ids = set(response.useful_sentence)

    return [
        sentence
        for sentence in sentences
        if sentence["id"] in selected_ids
    ]


  

def knoweldge_refinement(
    state: Agent_state
) -> Command[Literal["relevant", "not_relevant", "ambiguis"]]:

    if state["doc_class"] == "relevant":

        state["filtered_knowledge"] = _refine(
            state["query"],
            state["retrieved_docs"]
        )

        next_node = "relevant"

    elif state["doc_class"] == "irrelevant":

        state["filtered_web_knowledge"] = _refine(
            state["query"],
            state["websearch"]
        )

        next_node = "not_relevant"

    else:

        state["filtered_knowledge"] = _refine(
            state["query"],
            state["retrieved_docs"]
        )

        state["filtered_web_knowledge"] = _refine(
            state["query"],
            state["websearch"]
        )

        next_node = "ambiguis"

    return Command(
        update=state,
        goto=next_node
    )