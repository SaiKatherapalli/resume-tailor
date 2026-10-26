"""Manual check: talk to the LLM and see the result.

Run:  python scripts/try_llm.py
"""

from core.llm import get_chat_model, get_structured_llm
from core.schemas import JDAnalysis

# 1. Plain text answer
answer = get_chat_model().invoke("Give me 3 strong resume action verbs.")
print("TEXT ANSWER:\n", answer.content)

# 2. Structured answer (LLM fills the JDAnalysis form)
job_description = """
Backend Engineer. Build Java and Spring Boot microservices, use Kafka for events,
deploy on AWS with Docker and Kubernetes. PostgreSQL and REST APIs required.
"""
result = get_structured_llm(JDAnalysis).invoke("Analyze this job description:\n" + job_description)

print("\nSTRUCTURED ANSWER:")
print("Title:           ", result.job_title)
print("Responsibilities:", result.responsibilities)
print("Keywords:        ", result.keywords)
