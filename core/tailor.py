"""
One function that does the whole job: job description + career bank -> tailored resume.

The CLI calls this now. The API will call the SAME function later,
so the logic lives in one place.
"""

from collections.abc import Callable
from dataclasses import dataclass

from core.chains import build_chains
from core.embeddings import LocalEmbeddings
from core.graph import build_graph
from core.latex import render_resume
from core.retrieval import BulletIndex
from core.schemas import CareerBank, JDAnalysis, TailoredResume, bank_to_chunks
from core.validation import ValidationReport


@dataclass
class TailorResult:
    analysis: JDAnalysis
    report: ValidationReport  # the best attempt, already cleaned
    attempts: int
    tex: str

    @property
    def resume(self) -> TailoredResume:
        return self.report.resume


def tailor_resume(
    job_description: str,
    bank: CareerBank,
    api_key: str | None = None,
    on_step: Callable[[str, dict], None] | None = None,
) -> TailorResult:
    """
    on_step(node_name, update) is called after each graph step,
    so the caller can show progress (CLI prints it, the API will save it).
    """
    index = BulletIndex.build(bank_to_chunks(bank), LocalEmbeddings())
    graph = build_graph(build_chains(api_key))

    state = {"job_description": job_description, "bank": bank, "index": index}
    for step in graph.stream(state, stream_mode="updates"):
        for node, update in step.items():
            state.update(update)
            if on_step:
                on_step(node, update)

    report = state["best"]
    return TailorResult(
        analysis=state["analysis"],
        report=report,
        attempts=state["attempts"],
        tex=render_resume(bank, report.resume),
    )
