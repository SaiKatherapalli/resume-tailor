"""
LangChain chains: connect prompt + LLM + retrieval into one straight pipeline.

    job description -> analyze -> retrieve bullets -> rewrite -> TailoredResume

Each step ADDS a key to a dict, so later steps can use everything before them.
"""

import math
from dataclasses import dataclass

from langchain_core.runnables import Runnable, RunnablePassthrough

from core.llm import get_structured_llm
from core.prompts import analyze_prompt, rewrite_prompt
from core.retrieval import BulletIndex, BulletRetriever
from core.schemas import CareerBank, JDAnalysis, TailoredResume

CANDIDATE_MULTIPLIER = 1.6  # retrieve more bullets than we show, so the LLM can choose


@dataclass
class Chains:
    analyze: Runnable  # {job_description}  -> JDAnalysis
    rewrite: Runnable  # rewrite_prompt blanks -> TailoredResume


def build_chains(api_key: str | None = None) -> Chains:
    return Chains(
        analyze=analyze_prompt | get_structured_llm(JDAnalysis, api_key),
        rewrite=rewrite_prompt | get_structured_llm(TailoredResume, api_key),
    )


# ------------------------------------------------------------------ helpers


def split_keywords(bank: CareerBank, keywords: list[str]) -> tuple[list[str], list[str]]:
    """Which job keywords does the candidate really have? -> (have, missing)"""
    text = " ".join(
        [bank.summary, *bank.all_skills(), *(b for e in bank.experiences for b in e.bullets)]
    ).lower()
    have = [k for k in keywords if k.lower() in text]
    missing = [k for k in keywords if k.lower() not in text]
    return have, missing


def retrieve_candidates(bank: CareerBank, index: BulletIndex, analysis: JDAnalysis) -> dict[str, list]:
    """For each job, find the best bullets for this job description."""
    query = " ".join([analysis.job_title, *analysis.responsibilities, *analysis.keywords])
    return {
        exp.id: BulletRetriever(
            index=index, experience_id=exp.id, k=math.ceil(exp.max_bullets * CANDIDATE_MULTIPLIER)
        ).invoke(query)
        for exp in bank.experiences
    }


def build_rewrite_input(
    bank: CareerBank, analysis: JDAnalysis, candidates: dict[str, list], feedback: str = ""
) -> dict:
    """Fill every blank of rewrite_prompt."""
    have, _ = split_keywords(bank, analysis.keywords)
    experiences = []
    for exp in bank.experiences:
        docs = candidates[exp.id]
        lines = "\n".join(
            f"  [{d.metadata['id']}] ({len(d.page_content.split())} words) {d.page_content}" for d in docs
        )
        count = min(exp.max_bullets, len(docs))
        experiences.append(
            f"Experience id: {exp.id} | {exp.title}, {exp.company} | write {count} bullets\n{lines}"
        )
    return {
        "job_title": analysis.job_title,
        "responsibilities": "\n".join(f"- {r}" for r in analysis.responsibilities),
        "keywords": ", ".join(analysis.keywords),
        "honest_keywords": ", ".join(have) or "(none)",
        "original_summary": bank.summary,
        "skills_bank": "\n".join(f"{cat}: {', '.join(items)}" for cat, items in bank.skills.items()),
        "experiences": "\n\n".join(experiences),
        "feedback": feedback,
    }


# ------------------------------------------------------------------ the pipeline


def build_tailor_pipeline(chains: Chains) -> Runnable:
    """
    Input:  {"job_description": str, "bank": CareerBank, "index": BulletIndex}
    Output: the same dict + "analysis", "candidates", "resume"
    """
    return (
        RunnablePassthrough.assign(
            analysis=lambda x: chains.analyze.invoke({"job_description": x["job_description"]})
        )
        | RunnablePassthrough.assign(
            candidates=lambda x: retrieve_candidates(x["bank"], x["index"], x["analysis"])
        )
        | RunnablePassthrough.assign(
            resume=lambda x: chains.rewrite.invoke(
                build_rewrite_input(x["bank"], x["analysis"], x["candidates"])
            )
        )
    )
