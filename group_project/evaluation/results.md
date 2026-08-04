# RAG Evaluation Results

Framework: RAGAS-compatible offline proxy

## Overall Scores

| Metric | Config A: Hybrid + Rerank | Config B: Dense-only | Δ |
|---|---:|---:|---:|
| Faithfulness | 0.9505 | 1.0000 | -0.0495 |
| Answer Relevance | 0.7727 | 0.6021 | +0.1706 |
| Context Recall | 0.9375 | 0.7192 | +0.2183 |
| Context Precision | 1.0000 | 1.0000 | +0.0000 |
| **Average** | 0.9152 | 0.8303 | +0.0849 |

## A/B Comparison Analysis

Config A uses hybrid semantic + BM25 retrieval with RRF reranking.
Config B is the dense-only baseline.

## Worst Performers (Bottom 3)

| # | Question | Faithfulness | Relevance | Recall | Precision |
|---:|---|---:|---:|---:|---:|
| 1 | Làm sao xây dựng lịch trình du lịch tự túc tiết kiệm? | 0.945 | 0.273 | 0.944 | 1.000 |
| 2 | Hà Giang có những món đặc sản nào? | 0.962 | 0.625 | 0.750 | 1.000 |
| 3 | Đèo Mã Pì Lèng nằm ở đâu và có gì đặc biệt? | 0.965 | 0.500 | 0.895 | 1.000 |

## Recommendations

1. Tải BGE-M3 và reindex để tăng chất lượng semantic retrieval tiếng Việt.
2. Mở rộng golden dataset theo địa phương và loại câu hỏi.
3. Bật RAG_ENABLE_LLM_EVAL=1 khi có quota để đối chiếu proxy metrics với RAGAS judge.
