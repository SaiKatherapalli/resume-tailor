"""
LangGraph: the full tailoring flow, WITH a retry loop.

    analyze -> retrieve -> rewrite -> validate --ok--> END
                              ^           |
                              +--retry----+   (with feedback, max MAX_ATTEMPTS)

Why LangGraph and not a LangChain pipe?  A pipe only goes forward.
Here we must go BACK to "rewrite" when validation finds problems.

3 ideas:
  - State: one dict shared by all steps. Each node returns only the keys it changes.
  - Node:  a normal Python function  state -> {changed keys}.
  - Edge:  which node runs next. A conditional edge picks it with a function.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from core.chains import Chains, analyze_job, build_rewrite_input, retrieve_candidates
from core.retrieval import BulletIndex
from core.schemas import CareerBank, JDAnalysis, TailoredResume
from core.validation import ValidationReport, validate

MAX_ATTEMPTS = 3  # 1 try + 2 retries. Each try is an LLM call, so keep it small.


class TailorState(TypedDict, total=False):
    # input
    job_description: str
    bank: CareerBank
    index: BulletIndex
    # filled by the nodes
    analysis: JDAnalysis
    candidates: dict[str, list]
    resume: TailoredResume  # the latest LLM answer
    report: ValidationReport  # validation of the latest answer
    best: ValidationReport  # the best answer so far (fewest problems)
    attempts: int


def build_graph(chains: Chains):
    """Chains are passed in, so tests can use fake LLMs."""

    def analyze(state: TailorState) -> dict:
        return {"analysis": analyze_job(chains, state["job_description"])}

    def retrieve(state: TailorState) -> dict:
        return {"candidates": retrieve_candidates(state["bank"], state["index"], state["analysis"])}

    def rewrite(state: TailorState) -> dict:
        report = state.get("report")
        feedback = report.feedback() if report and not report.ok else ""
        inputs = build_rewrite_input(state["bank"], state["analysis"], state["candidates"], feedback)
        return {"resume": chains.rewrite.invoke(inputs), "attempts": state.get("attempts", 0) + 1}

    def check(state: TailorState) -> dict:
        report = validate(state["bank"], state["analysis"], state["resume"])
        best = state.get("best")
        if best is None or len(report.issues) <= len(best.issues):
            best = report
        return {"report": report, "best": best}

    def next_step(state: TailorState) -> str:
        if state["report"].ok or state["attempts"] >= MAX_ATTEMPTS:
            return "done"
        return "retry"

    graph = StateGraph(TailorState)
    graph.add_node("analyze", analyze)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rewrite", rewrite)
    graph.add_node("validate", check)

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "rewrite")
    graph.add_edge("rewrite", "validate")
    graph.add_conditional_edges("validate", next_step, {"retry": "rewrite", "done": END})

    return graph.compile()
