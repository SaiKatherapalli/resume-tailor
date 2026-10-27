"""See embeddings in action: which of YOUR bullets match a job need best?

Run:  python scripts/try_embeddings.py "deploy apps with Docker and Kubernetes"
"""

import sys

import numpy as np

from core.career_bank import load_career_bank
from core.embeddings import LocalEmbeddings
from core.schemas import bank_to_chunks

query = sys.argv[1] if len(sys.argv) > 1 else "event streaming with Kafka"
chunks = bank_to_chunks(load_career_bank("data/career_bank.yaml"))

emb = LocalEmbeddings()
bullet_vectors = np.array(emb.embed_documents([c.text for c in chunks]))
query_vector = np.array(emb.embed_query(query))

print(f"One vector = {len(query_vector)} numbers. First 5: {np.round(query_vector[:5], 3)}\n")

# cosine similarity = how close two meanings are (1 = same, 0 = unrelated)
scores = (
    bullet_vectors @ query_vector / (np.linalg.norm(bullet_vectors, axis=1) * np.linalg.norm(query_vector))
)

print(f'Top 5 bullets for: "{query}"\n')
for i in np.argsort(-scores)[:5]:
    print(f"{scores[i]:.3f}  [{chunks[i].id}]  {chunks[i].text[:90]}...")
