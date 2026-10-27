"""See hybrid search pick the best bullets PER JOB.

Run:  python scripts/try_retrieval.py "Java Spring Boot microservices with Kafka on AWS"
"""

import sys

from core.career_bank import load_career_bank
from core.embeddings import LocalEmbeddings
from core.retrieval import BulletIndex, BulletRetriever
from core.schemas import bank_to_chunks

query = sys.argv[1] if len(sys.argv) > 1 else "Java Spring Boot microservices with Kafka on AWS"
bank = load_career_bank("data/career_bank.yaml")
index = BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())

print(f'Search: "{query}"')
for exp in bank.experiences:
    retriever = BulletRetriever(index=index, k=3, experience_id=exp.id)
    print(f"\n== {exp.company} ==")
    for doc in retriever.invoke(query):
        print(f"  {doc.metadata['score']:.4f} [{doc.metadata['id']}] {doc.page_content[:85]}...")
