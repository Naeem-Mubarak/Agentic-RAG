from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
load_dotenv()
from huggingface_hub import InferenceClient


def embedding_generation(text):

    """
    downloading Qwen 0.6B model for creating embeddings 
    """

    if not text:
        raise ValueError("Text can't be empty")

    hf_token = os.getenv("HF_TOKEN")

    if hf_token:

        try:
            client = InferenceClient(token = hf_token)
            embedding = client.feature_extraction(
                text=text,
                model="Qwen/Qwen3-Embedding-8B"
            )

            return embedding

        except Exception:
            pass

    try:

        model = SentenceTransformer(
            "Qwen/Qwen3-Embedding-0.6B",
            token = os.getenv("HF_TOKEN")
        )
        embedding = model.encode(text)

        return embedding

    except Exception as e:

       raise ValueError(f"Fail to create embeddings \n Error Details: {e}")
        

    

def embedding_chunks(chunks):


    """
    formatting the chunk data by adding embedding for that particular content
    every chunk have
    1. page_content
    2. embedding
    3. metadata
    """

    chunks_with_embeeding = []

    content = []
    for chunk in chunks:
        content.append(chunk.page_content)

    embedding = embedding_generation(content)

    for index,chunk in enumerate(chunks,start=0):
        chunks_with_embeeding.append({
            "page_content" : chunk.page_content,
            "embeddings" : embedding[index],
            "metadata" : chunk.metadata
        })


    return chunks_with_embeeding


