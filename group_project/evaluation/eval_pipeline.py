"""Offline-friendly RAG evaluation for the travel assistant.

The evaluator exposes a RAGAS-compatible interface. Set RAG_ENABLE_LLM_EVAL=1
to call RAGAS with an LLM judge; otherwise deterministic proxy metrics are used
so the report can be reproduced without consuming API quota.
"""

import json
import os
import re
from pathlib import Path

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"


def load_golden_dataset() -> list[dict]:
    return json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE))


def _evaluate_case(item: dict, result: dict) -> dict:
    answer = result.get("answer", "")
    contexts = [c.get("content", "") for c in result.get("sources", [])]
    context_text = " ".join(contexts)
    q = _tokens(item["question"])
    expected = _tokens(item.get("expected_answer", ""))
    answer_tokens = _tokens(answer)
    context_tokens = _tokens(context_text)
    faithfulness = len(answer_tokens & context_tokens) / max(1, len(answer_tokens))
    relevance = len(q & answer_tokens) / max(1, len(q))
    recall = len(expected & context_tokens) / max(1, len(expected))
    useful = sum(1 for context in contexts if _tokens(context) & q)
    precision = useful / max(1, len(contexts))
    return {"question": item["question"], "faithfulness": round(min(1, faithfulness), 4), "answer_relevance": round(min(1, relevance), 4), "context_recall": round(min(1, recall), 4), "context_precision": round(min(1, precision), 4), "sources": len(contexts)}


def evaluate_with_ragas(rag_pipeline, golden_dataset: list[dict]) -> dict:
    """Evaluate with RAGAS when explicitly enabled, otherwise offline proxies."""
    cases = []
    for item in golden_dataset:
        result = rag_pipeline.generate_with_citation(item["question"])
        cases.append(_evaluate_case(item, result))
    if os.getenv("RAG_ENABLE_LLM_EVAL", "").lower() not in {"1", "true", "yes"}:
        return {"framework": "RAGAS-compatible offline proxy", "cases": cases}
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
        data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
        for item in golden_dataset:
            result = rag_pipeline.generate_with_citation(item["question"])
            data["question"].append(item["question"]); data["answer"].append(result["answer"])
            data["contexts"].append([c.get("content", "") for c in result.get("sources", [])]); data["ground_truth"].append(item["expected_answer"])
        frame = evaluate(Dataset.from_dict(data), metrics=[faithfulness, answer_relevancy, context_recall, context_precision]).to_pandas()
        return {"framework": "RAGAS", "cases": frame.to_dict("records"), "overall": frame.mean(numeric_only=True).to_dict()}
    except Exception as exc:
        return {"framework": "RAGAS-compatible offline proxy", "cases": cases, "warning": str(exc)}


def evaluate_with_deepeval(rag_pipeline, golden_dataset):
    return evaluate_with_ragas(rag_pipeline, golden_dataset)


def evaluate_with_trulens(rag_pipeline, golden_dataset):
    return evaluate_with_ragas(rag_pipeline, golden_dataset)


def _averages(cases: list[dict]) -> dict:
    metrics = ["faithfulness", "answer_relevance", "context_recall", "context_precision"]
    return {metric: round(sum(float(c.get(metric, 0)) for c in cases) / max(1, len(cases)), 4) for metric in metrics}


def compare_configs(rag_pipeline, golden_dataset: list[dict]):
    a = evaluate_with_ragas(rag_pipeline, golden_dataset)
    # Config B: genuine dense-only retrieval baseline (no BM25/RRF).
    from src.task5_semantic_search import semantic_search
    dense_cases = []
    for item in golden_dataset:
        sources = semantic_search(item["question"], top_k=5)
        answer = sources[0].get("content", "") if sources else ""
        dense_cases.append(_evaluate_case(item, {"answer": answer, "sources": sources}))
    b = {"framework": a.get("framework"), "cases": dense_cases}
    return {"hybrid_rerank": {"averages": _averages(a["cases"]), "cases": a["cases"]}, "dense_only": {"averages": _averages(b["cases"]), "cases": b["cases"]}}


def export_results(results: dict, comparison: dict):
    metrics = [("faithfulness", "Faithfulness"), ("answer_relevance", "Answer Relevance"), ("context_recall", "Context Recall"), ("context_precision", "Context Precision")]
    a = comparison["hybrid_rerank"]["averages"]; b = comparison["dense_only"]["averages"]
    lines = ["# RAG Evaluation Results", "", f"Framework: {results.get('framework', 'RAGAS')}", "", "## Overall Scores", "", "| Metric | Config A: Hybrid + Rerank | Config B: Dense-only | Δ |", "|---|---:|---:|---:|"]
    for key, label in metrics: lines.append(f"| {label} | {a[key]:.4f} | {b[key]:.4f} | {a[key]-b[key]:+.4f} |")
    lines.append(f"| **Average** | {sum(a.values())/4:.4f} | {sum(b.values())/4:.4f} | {(sum(a.values())-sum(b.values()))/4:+.4f} |")
    lines += ["", "## A/B Comparison Analysis", "", "Config A uses hybrid semantic + BM25 retrieval with RRF reranking.", "Config B is the dense-only baseline.", "", "## Worst Performers (Bottom 3)", "", "| # | Question | Faithfulness | Relevance | Recall | Precision |", "|---:|---|---:|---:|---:|---:|"]
    worst = sorted(comparison["hybrid_rerank"]["cases"], key=lambda c: sum(c.get(k, 0) for k, _ in metrics))[:3]
    for i, case in enumerate(worst, 1): lines.append(f"| {i} | {case['question']} | {case.get('faithfulness',0):.3f} | {case.get('answer_relevance',0):.3f} | {case.get('context_recall',0):.3f} | {case.get('context_precision',0):.3f} |")
    lines += ["", "## Recommendations", "", "1. Tải BGE-M3 và reindex để tăng chất lượng semantic retrieval tiếng Việt.", "2. Mở rộng golden dataset theo địa phương và loại câu hỏi.", "3. Bật RAG_ENABLE_LLM_EVAL=1 khi có quota để đối chiếu proxy metrics với RAGAS judge.", ""]
    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    from src.task10_generation import generate_with_citation
    class Pipeline:
        generate_with_citation = staticmethod(generate_with_citation)
    dataset = load_golden_dataset()
    results = evaluate_with_ragas(Pipeline, dataset)
    comparison = compare_configs(Pipeline, dataset)
    export_results(results, comparison)
    print(f"Evaluated {len(dataset)} cases; wrote {RESULTS_PATH}")