import numpy as np

from core.embeddings import LocalEmbeddings


def cosine(a, b) -> float:
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_vector_size():
    vectors = LocalEmbeddings().embed_documents(["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384  # bge-small makes 384 numbers per text


def test_similar_meaning_scores_higher():
    emb = LocalEmbeddings()
    query = emb.embed_query("event streaming with Apache Kafka")
    kafka_bullet, agile_bullet = emb.embed_documents([
        "Integrated Kafka for asynchronous communication between microservices.",
        "Participated in sprint planning and retrospectives.",
    ])
    assert cosine(query, kafka_bullet) > cosine(query, agile_bullet)
