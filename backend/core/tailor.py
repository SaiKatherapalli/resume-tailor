"""
One function that does the whole job: job description + career bank -> tailored resume.

The CLI calls this now. The API will call the SAME function later,
so the logic lives in one place.
"""

import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from core.chains import build_chains
from core.embeddings import LocalEmbeddings
from core.graph import build_graph
from core.latex import render_resume
from core.retrieval import BulletIndex
from core.schemas import CareerBank, JDAnalysis, TailoredResume, bank_to_chunks
from core.validation import ValidationReport

log = logging.getLogger(__name__)

# Embedding a bank is slow on a small server and gives the same result every time,
# so keep the last few indexes (keyed by the bullets' text, so an edited bank is re-embedded).
_INDEX_CACHE: OrderedDict[str, BulletIndex] = OrderedDict()
_INDEX_CACHE_SIZE = 8


def _index_for(bank: CareerBank) -> BulletIndex:
    chunks = bank_to_chunks(bank)
    key = hashlib.sha256("\x00".join(f"{c.id}\x01{c.text}" for c in chunks).encode()).hexdigest()
    if key in _INDEX_CACHE:
        _INDEX_CACHE.move_to_end(key)
        return _INDEX_CACHE[key]
    index = BulletIndex.build(chunks, LocalEmbeddings())
    _INDEX_CACHE[key] = index
    while len(_INDEX_CACHE) > _INDEX_CACHE_SIZE:
        _INDEX_CACHE.popitem(last=False)
    return index


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
    started = last = time.perf_counter()
    index = _index_for(bank)
    graph = build_graph(build_chains(api_key))
    log.info("tailor: index ready in %.1fs", time.perf_counter() - last)

    state = {"job_description": job_description, "bank": bank, "index": index}
    last = time.perf_counter()
    for step in graph.stream(state, stream_mode="updates"):
        for node, update in step.items():
            state.update(update)
            log.info("tailor: %s took %.1fs", node, time.perf_counter() - last)
            last = time.perf_counter()
            if on_step:
                on_step(node, update)
    log.info("tailor: total %.1fs, %d attempt(s)", time.perf_counter() - started, state["attempts"])

    report = state["best"]
    return TailorResult(
        analysis=state["analysis"],
        report=report,
        attempts=state["attempts"],
        tex=render_resume(bank, report.resume),
    )
