import os
import chromadb
import numpy as np
from chromadb import Documents, EmbeddingFunction, Embeddings

class UpstageEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(
        self,
        client,
        model_name: str = "embedding-query",
    ):
        self.client = client
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        if not all(isinstance(item, str) for item in input):
            raise ValueError("Solar embedding only supports text documents, not images")

        batch_process_result = self.client.embeddings.create(model=self.model_name, input=input).data
        passage_embedding_list = [i.embedding for i in batch_process_result]
        return np.array(passage_embedding_list, dtype=np.float32)

def get_upstage_embedding_fn(client):
    embedding_fn = UpstageEmbeddingFunction(client)
    return embedding_fn