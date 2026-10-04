from dotenv import load_dotenv
import os
load_dotenv()
from huggingface_hub import InferenceClient
from google import genai
from google.genai import types



def embedding_generation(texts):

    """
    There are two free options for generating embeddings one is Google's Gemini model and other is one of the best opensource model named Qwen an 8B parameter model in the top 5 of the MTEB benchmark in Hugging face 
    use one of them which free tier is available

    Note: Creating embeddings of dimension 2000 because we want to create HNSW index for fast retrieval
    """
    model_used = ''

    if not texts:
        raise ValueError("Text can't be empty")

    hf_token = os.getenv("HF_TOKEN")

    if hf_token:

        try:

            # using one of the best opensoruce embedding models (Using the free tier) if it reaches it's limit then will download one of it's variant given below
            client = InferenceClient(token = hf_token)
            embedding = client.feature_extraction(
                text=texts,
                model="Qwen/Qwen3-Embedding-8B",
                dimensions = 2000
            )
            model_used = 'HF'
            return embedding, model_used

        except Exception as e:
            pass

    try:

        client = genai.Client()
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality = 2000
            )
        )
        model_used = 'gemini'

        print("Embedding generated successfully")

        return result, model_used
    
    except Exception as e:
    
        raise ValueError(f"Fail to create embeddings \n Error Details: {e}")

        

    

def embedding_chunks(chunks, batch_size : int = 100):


    """
    formatting the chunk data by adding embedding for that particular content
    every chunk have
    1. page_content
    2. embedding
    3. metadata
    """
    
    # isolating the page content and metadata
    page_contents = [doc.page_content for doc in chunks]
    metadata = [doc.metadata for doc in chunks]

    # creating batches of page_content
    batches = [page_contents[i:i+batch_size] for i in range(0, len(page_contents), batch_size)]


    # looping through every batch and then create it's embedding and then isolating embedding of each content from it's batch
    final_embeddings = []
    for batch in batches:
        result, model_used = embedding_generation(batch)
        if model_used == 'gemini':

            batch_embeddings = [e.values for e in result.embeddings]
            for embed in batch_embeddings:
                final_embeddings.append(embed)
        else:
            for embed in result:
                final_embeddings.append(embed)

    
    chunks_with_embedding = []

    # final schema in which every content is isolated from other's with it's embeddings and metadata 
    for i in range(len(page_contents)):
        chunks_with_embedding.append({
            "page_content" : page_contents[i],
            "embeddings" : final_embeddings[i],
            "metadata" : metadata[i]
        })

    print("Chunks with Embeddings are ready")
    return chunks_with_embedding


