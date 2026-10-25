# Final Evidence-Based Audit & Comparative Evaluation Report: Orbit AI Phase 3
**Evaluation Framework Version:** Rubric 2.2-deterministic-audited  
**Date of Audit:** 2026-10-25  
**Audit Scope:** Full 100-Question Benchmark, Empirical Verification & Model Comparison  

---

## 1. Executive Summary & Research Question

### 1.1 Core Research Question
Does providing a large language model with integrated tool access across multiple enterprise workspace surfaces (unstructured documentation, structured task trackers, and real-time team chat) measurably improve factual correctness and faithfulness on collaborative, multi-source workspace questions compared with a bare language model (`plain_llm`) or document-only retrieval (`rag_docs_only`)?

### 1.2 Summary of Empirical Findings
1. **Multi-Source Superiority (Gemini 3.5 Flash Lite):**
   On genuine multi-source questions in the held-out evaluation cohort (Q53–Q84, $n=32$), `full_agent` achieved **84.38%** factual correctness compared to **40.62%** for `rag_docs_only` (+**43.75 percentage points** improvement) and **0.00%** for `plain_llm`. Across all 40 multi-source questions in the full dataset, `full_agent` scored **70.00%** vs. **33.75%** for `rag_docs_only` (+**36.25 percentage points**). This strongly confirms the hypothesis that tool-augmented agents are necessary to synthesize facts distributed across disparate enterprise surfaces.
2. **Model Scaling and Architectural Disparity (Gemini vs. Llama 3.2):**
   - **Gemini 3.5 Flash Lite** effectively utilized multi-tool orchestration, increasing overall correctness from 22.50% (`plain_llm`) to 53.00% (`rag_docs_only`) and reaching **74.50%** in `full_agent`.
   - **Llama 3.2:latest (3.2B local)** improved substantially from 5.50% (`plain_llm`) to 45.50% (`rag_docs_only`), but showed limited overall improvement in `full_agent` (**47.00%**, +1.50 pp over RAG). While Llama 3.2 successfully invoked agent tools (calling up to 3 tools in sequence), its smaller parameter capacity frequently struggled with cross-source contextual synthesis and hallucinated plausible-sounding answers when evidence was missing.
3. **Execution Robustness:**
   Both models completed all 300 scheduled attempts across all 3 configurations with **100% execution success** (0 network timeouts, 0 rate limits, 0 database errors).

---

## 2. Experimental Design & Configuration Definitions

The benchmark rigorously isolates the contribution of each enterprise information channel across three controlled configurations:

| Configuration | Document RAG Access | Task Tracker Access (`get_tasks`) | Chat Message Access (`get_chat`) | Pre-injected Context | System Prompt Tools Bound |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`plain_llm`** | ❌ No | ❌ No | ❌ No | None | None |
| **`rag_docs_only`** | ✅ Vector search | ❌ No | ❌ No | Top-3 chunk passages | Tool-restricted |
| **`full_agent`** | ✅ Vector search | ✅ SQL task lookup | ✅ Chat history | Top-3 chunk passages | All tools (`search_workspace_tool`, `get_tasks_tool`, `get_chat_history_tool`) |

- **Target Workspace:** Workspace 3 (`00000000-0000-4000-8000-000000000003`), populated with 3 active architecture/security/release specification documents, 16 sprint tasks, and 16 team chat messages.
- **Evaluation Temperature:** 0.3 across all runs to ensure deterministic factual evaluation.
- **Context Windows:** Gemini API native; Ollama `num_ctx = 8192`.

---

## 3. Dataset Composition & Corrected Cohort/Category Definitions

### 3.1 Correction of Naive ID-Range Assumptions
Previous preliminary comparisons incorrectly assumed that question IDs mapped linearly to single categories (e.g. assuming Q01–Q40 were single-source, Q41–Q80 were multi-source, and Q81–Q100 were unanswerable). 

**Authoritative Analysis:** Question categories in `questions_phase3_100.json` are determined strictly by the `category` attribute, which partitions into two distinct historical cohorts:

```
Full Dataset (100 Questions)
├── Baseline / Historical Cohort (Q01–Q20, n=20)
│   ├── single_source: 8 questions (Q01–Q08)
│   ├── multi_source : 8 questions (Q09–Q16)
│   └── unanswerable : 4 questions (Q17–Q20)
└── Phase 3 Held-Out Cohort (Q21–Q100, n=80)
    ├── single_source: 32 questions (Q21–Q52)
    ├── multi_source : 32 questions (Q53–Q84)
    └── unanswerable : 16 questions (Q85–Q100)
```

### 3.2 Category Breakdown & Denominators

| Cohort | `single_source` | `multi_source` | `unanswerable` | Total Questions |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline Cohort (Q01–Q20)** | 8 (40.0%) | 8 (40.0%) | 4 (20.0%) | **20** |
| **Held-Out Cohort (Q21–Q100)** | 32 (40.0%) | 32 (40.0%) | 16 (20.0%) | **80** |
| **Full Combined Dataset (Q01–Q100)** | **40 (40.0%)** | **40 (40.0%)** | **20 (20.0%)** | **100** |

**Why Baseline Cohort Scores Differ:** The Baseline cohort (Q01–Q20) was originally authored against Phase 2 synthetic workspaces (Workspaces 1 & 2), referencing entities such as "Implement Redis connection pooling". Because Workspace 3 contains Sprint 15 documents and tasks ("P0/P1 defect triage", "document export feature"), models correctly abstain or cannot find these Phase 2 records, resulting in expected domain mismatch scores (~0.20–0.28). The Phase 3 Held-Out Cohort (Q21–Q100) was tailored specifically to Workspace 3 records.

---

## 4. Execution Integrity & Provenance Verification

Every attempt was programmatically audited across the raw `.jsonl` execution streams and the final scored `.json` reports:

| Audit Criterion | Gemini 3.5 Flash Lite Run | Llama 3.2:latest Run | Status |
| :--- | :--- | :--- | :---: |
| **Unique Run ID** | `phase3_benchmark_gemini_35_lite_20261025_165427` | `phase3_benchmark_llama32_20261025_173645` | Verified |
| **Raw Result File** | `results/phase3_benchmark_gemini_35_lite_...jsonl` | `results/phase3_benchmark_llama32_...jsonl` | Verified |
| **Raw Attempt Count** | Exactly 300 records | Exactly 300 records | Verified |
| **Question-Config Coverage** | 100 questions × 3 configs (no duplicates, no gaps) | 100 questions × 3 configs (no duplicates, no gaps) | Verified |
| **Execution Status** | 300 successes, 0 failures, 0 errors | 300 successes, 0 failures, 0 errors | 100% |
| **Scored Report File** | `reports/scored_..._corrected.json` | `reports/scored_..._llama32_...json` | Verified |
| **Rubric Version** | `2.2-deterministic-audited` | `2.2-deterministic-audited` | Identical |
| **Metadata Parity** | `meta_phase3_benchmark_gemini_35_lite_...json` | `meta_phase3_benchmark_llama32_...json` | Verified |

---

## 5. Correctness, Faithfulness & Latency Reconciliation

### 5.1 Full Dataset Benchmark Reconciliation (Q01–Q100, 300 Attempts Per Model)

| Metric | Gemini `plain_llm` | Gemini `rag_docs_only` | Gemini `full_agent` | Llama `plain_llm` | Llama `rag_docs_only` | Llama `full_agent` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall Correctness** | **0.2250** | **0.5300** | **0.7450** | **0.0550** | **0.4550** | **0.4700** |
| *Full Credit (1.0)* | 22 | 39 | 69 | 4 | 33 | 35 |
| *Partial Credit (0.5)* | 1 | 28 | 11 | 3 | 25 | 24 |
| *Zero Credit (0.0)* | 77 | 33 | 20 | 93 | 42 | 41 |
| **Faithfulness Mean** | **1.0000** | **0.8350** | **0.9000** | **0.1000** | **0.7550** | **0.7500** |
| *Faithfulness Evaluated* | 20 (Unans only) | 100 | 100 | 20 (Unans only) | 100 | 100 |
| *Faithfulness Non-evaluable* | 80 (No retrieved ev) | 0 | 0 | 80 (No retrieved ev) | 0 | 0 |
| **Execution Success Rate** | 100% (100/100) | 100% (100/100) | 100% (100/100) | 100% (100/100) | 100% (100/100) | 100% (100/100) |
| **Mean Latency** | 1,332 ms (1.33s) | 5,910 ms (5.91s) | 6,415 ms (6.42s) | 6,300 ms (6.30s) | 18,028 ms (18.03s) | 19,496 ms (19.50s) |
| **Median Latency** | 912 ms (0.91s) | 4,094 ms (4.09s) | 5,998 ms (6.00s) | 5,727 ms (5.73s) | 17,918 ms (17.92s) | 19,609 ms (19.61s) |

*Note on Faithfulness Methodology:* `plain_llm` possesses no retrieved evidence; per rubric specification, faithfulness is evaluated strictly on unanswerable questions (where producing a refusal without hallucinated forbidden entities equals 1.0). For RAG and Agent configurations, all 100 attempts retrieve evidence and are evaluated against retrieved source chunks.

---

## 6. Category-Level Results (Full Dataset, $N=100$)

| Model & Category | Config | Attempts | Mean Correctness | Partial Credits | Mean Faithfulness | Evaluated Count |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.5 Flash Lite** | | | | | | |
| *Single-Source* | `plain_llm` | 40 | 0.0625 | 1 | N/A | 0 |
| | `rag_docs_only` | 40 | 0.4875 | 1 | 0.7500 | 40 |
| | `full_agent` | 40 | **0.6625** | 1 | **0.8375** | 40 |
| *Multi-Source* | `plain_llm` | 40 | 0.0000 | 0 | N/A | 0 |
| | `rag_docs_only` | 40 | 0.3375 | 27 | 0.8375 | 40 |
| | `full_agent` | 40 | **0.7000** | 10 | **0.9125** | 40 |
| *Unanswerable* | `plain_llm` | 20 | 1.0000 | 0 | 1.0000 | 20 |
| | `rag_docs_only` | 20 | 1.0000 | 0 | 1.0000 | 20 |
| | `full_agent` | 20 | **1.0000** | 0 | **1.0000** | 20 |
| **Llama 3.2:latest** | | | | | | |
| *Single-Source* | `plain_llm` | 40 | 0.0750 | 2 | N/A | 0 |
| | `rag_docs_only` | 40 | 0.4500 | 0 | 0.7250 | 40 |
| | `full_agent` | 40 | 0.4250 | 0 | 0.7125 | 40 |
| *Multi-Source* | `plain_llm` | 40 | 0.0125 | 1 | N/A | 0 |
| | `rag_docs_only` | 40 | 0.3125 | 25 | 0.7875 | 40 |
| | `full_agent` | 40 | **0.4000** | 24 | **0.8125** | 40 |
| *Unanswerable* | `plain_llm` | 20 | 0.1000 | 0 | 0.1000 | 20 |
| | `rag_docs_only` | 20 | 0.7500 | 0 | 0.7500 | 20 |
| | `full_agent` | 20 | 0.7000 | 0 | 0.7000 | 20 |

---

## 7. Baseline Cohort vs. Held-Out Cohort Breakdown

### 7.1 Baseline Cohort (Q01–Q20, $n=20$)
Questions written against Phase 2 tasks (absent in Workspace 3):

| Category ($n$) | Configuration | Gemini Correctness | Llama Correctness |
| :--- | :--- | :---: | :---: |
| **Single-Source (8)** | `plain_llm` | 0.0000 | 0.0625 |
| | `rag_docs_only` | 0.0625 | 0.1250 |
| | `full_agent` | 0.0625 | 0.1250 |
| **Multi-Source (8)** | `plain_llm` | 0.0000 | 0.0000 |
| | `rag_docs_only` | 0.0625 | 0.1250 |
| | `full_agent` | 0.1250 | 0.1250 |
| **Unanswerable (4)** | `plain_llm` | 1.0000 | 0.2500 |
| | `rag_docs_only` | 1.0000 | 0.7500 |
| | `full_agent` | 1.0000 | 0.7500 |
| **Baseline Total (20)** | `plain_llm` | 0.2000 | 0.0750 |
| | `rag_docs_only` | 0.2500 | 0.2500 |
| | `full_agent` | **0.2750** | **0.2500** |

---

### 7.2 Phase 3 Held-Out Cohort (Q21–Q100, $n=80$)
Questions specifically written and validated against Workspace 3:

| Category ($n$) | Configuration | Gemini Correctness | Llama Correctness | Delta (Gemini vs. Llama) |
| :--- | :--- | :---: | :---: | :---: |
| **Single-Source (32)** | `plain_llm` | 0.0781 | 0.0781 | 0.00 pp |
| | `rag_docs_only` | 0.5938 | 0.5312 | +6.26 pp |
| | `full_agent` | **0.8125** | 0.5000 | **+31.25 pp** |
| **Multi-Source (32)** | `plain_llm` | 0.0000 | 0.0156 | -1.56 pp |
| | `rag_docs_only` | 0.4062 | 0.3594 | +4.68 pp |
| | `full_agent` | **0.8438** | **0.4688** | **+37.50 pp** |
| **Unanswerable (16)** | `plain_llm` | 1.0000 | 0.0625 | +93.75 pp |
| | `rag_docs_only` | 1.0000 | 0.7500 | +25.00 pp |
| | `full_agent` | **1.0000** | 0.6875 | +31.25 pp |
| **Held-Out Total (80)** | `plain_llm` | 0.2313 | 0.0500 | +18.13 pp |
| | `rag_docs_only` | 0.6000 | 0.5062 | +9.38 pp |
| | `full_agent` | **0.8625** | **0.5250** | **+33.75 pp** |

---

## 8. Incremental Configuration Deltas (Percentage Points)

| Evaluation Slice | Gemini: RAG over Plain ($\Delta$) | Gemini: Agent over RAG ($\Delta$) | Llama: RAG over Plain ($\Delta$) | Llama: Agent over RAG ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Dataset (Q01–Q100)** | +30.50 pp | **+21.50 pp** | +40.00 pp | +1.50 pp |
| **Multi-Source (All 40)** | +33.75 pp | **+36.25 pp** | +30.00 pp | **+8.75 pp** |
| **Single-Source (All 40)** | +42.50 pp | **+17.50 pp** | +37.50 pp | -2.50 pp |
| **Held-Out Multi-Source (Q53–Q84)** | +40.62 pp | **+43.75 pp** | +34.38 pp | **+10.94 pp** |
| **Held-Out Single-Source (Q21–Q52)** | +51.56 pp | **+21.88 pp** | +45.31 pp | -3.12 pp |
| **Held-Out Unanswerable (Q85–Q100)** | 0.00 pp | 0.00 pp | +68.75 pp | -6.25 pp |

---

## 9. Targeted Question Audit (Q21, Q53, Q85, Q93, Q99)

### Q21: API REST Endpoint Prefix (`/api/v2`)
- **Criteria:** Exact match on `/api/v2`; reject `/api/v1`.
- **Gemini Outcome:** `rag_docs_only` = **1.0**, `full_agent` = **1.0**. Scored perfectly under relaxed markdown punctuation lookahead (`` `/api/v2` ``).
- **Llama Outcome:** `rag_docs_only` = **1.0**, `full_agent` = **1.0**. Answered `/api/v2` without contradiction.

### Q53: Multi-Source Synthesis (11 Nov Release Candidate & 7 Nov Task Deadline)
- **Criteria:** Synthesize 11 November 2026 (release plan document) and 7 November 2026 (task tracker T01).
- **Gemini Outcome:**
  - `rag_docs_only` = **0.5** (truthfully stated task due date not found in documents).
  - `full_agent` = **1.0** (Corr: 1.0, Faith: 1.0). Invoked `get_tasks_tool`, synthesized both dates accurately.
- **Llama Outcome:**
  - `rag_docs_only` = **0.0** (partial text presence failed exact multi-source requirements).
  - `full_agent` = **0.5** (Corr: 0.5, Faith: 1.0). Invoked `['get_tasks_tool', 'search_workspace_tool']`; extracted 11 November 2026, but claimed no task was found for document export.

### Q85: Mobile App Unanswerable Refusal vs. 16 Nov Web Hallucination
- **Criteria:** Refuse exact mobile app date; forbid hallucinating 16 November 2026 (web release date).
- **Gemini Outcome:** `rag_docs_only` = **1.0**, `full_agent` = **1.0**. Distinguished "mobile layout fixes" from a dedicated app release; refused without fabricating dates.
- **Llama Outcome:**
  - `rag_docs_only` = **0.0** (Corr: 0.0, Faith: 0.0). **Hallucinated:** Stated 16 November 2026 as the mobile app target release date.
  - `full_agent` = **1.0** (Corr: 1.0, Faith: 1.0). Invoked `get_tasks_tool`, verified only mobile layout fixes exist, and properly refused.

### Q93 & Q99: Plural Refusal Language Audit
- **Issue Investigated:** In initial runs, Gemini `full_agent` responses using plural agreement (*"documents and task records do not contain information"*) failed `does not contain` matching.
- **Rubric 2.2 Verification:** Under Rubric 2.2, both Q93 and Q99 score **1.0** Corr and **1.0** Faith.
- **Llama Behavior on Q93 & Q99:**
  - Q93 `full_agent`: Hallucinated *"The on-call engineer for the production API this weekend is Omar"* (Score: **0.0**).
  - Q99 `full_agent`: Hallucinated *"The final press release wording was approved by Omar on 15 November 2026, at 10:00 AM UTC"* (Score: **0.0**).
  - Proves Rubric 2.2 strictly fails unsupported fabricated answers while accepting valid semantic refusals.

---

## 10. Major Error Patterns & Evidence

1. **Hallucinatory Extrapolation in Document-Only RAG:**
   When questions inquire about entities not in documents, `rag_docs_only` models often latch onto adjacent facts (e.g. Llama extrapolating web app dates to mobile queries in Q85).
2. **Tool-Call Distraction in Smaller Local Models:**
   On single-source document questions, Llama 3.2 scored higher in `rag_docs_only` (53.12%) than in `full_agent` (50.00%). The presence of multiple tool options occasionally distracted the 3.2B model into checking task/chat tools unnecessarily instead of directly answering from pre-injected context.
3. **Cross-Source Attribute Binding Failures:**
   In complex multi-source questions (e.g. Q53), Llama often retrieved the correct task payload via `get_tasks_tool` but failed to extract or correlate the specific assignee's due date in its final synthesis prompt.

---

## 11. Threats to Validity & Limitations

1. **Synthetic Workspace Scope:**
   Workspace 3 comprises 3 documents, 16 tasks, and 16 chat messages. While representative of an enterprise sprint, production environments feature thousands of records where retrieval recall and token limits become more challenging.
2. **Deterministic Regex Scoring Limitations:**
   Deterministic keyword/entity matching eliminates LLM-as-a-judge bias but requires strict regex lookarounds and synonym dictionaries. Semantic phrasing variations (like the singular/plural issue resolved in Rubric 2.2) require ongoing validation.
3. **Hardware & Environment Confounding:**
   Gemini 3.5 Flash Lite ran via cloud API, whereas Llama 3.2 ran locally via Ollama with CPU/GPU offload. Latency comparisons reflect the operational reality of cloud APIs vs. local edge inference rather than raw architectural token generation speed.

---

## 12. Artifact Inventory & Reproducibility

All evaluation artifacts are preserved in the repository:

- **Canonical Dataset:** [`backend/evaluation/questions_phase3_100.json`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/questions_phase3_100.json)
- **Scoring Engine:** [`backend/evaluation/score_results.py`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/score_results.py) (Rubric `2.2-deterministic-audited`)
- **Evaluation Runner:** [`backend/evaluation/run_evaluation.py`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/run_evaluation.py)
- **Raw Execution Results:**
  - Gemini: [`backend/evaluation/results/phase3_benchmark_gemini_35_lite_20261025_165427.jsonl`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/results/phase3_benchmark_gemini_35_lite_20261025_165427.jsonl)
  - Llama 3.2: [`backend/evaluation/results/phase3_benchmark_llama32_20261025_173645.jsonl`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/results/phase3_benchmark_llama32_20261025_173645.jsonl)
- **Final Scored Reports:**
  - Gemini Corrected: [`backend/evaluation/reports/scored_phase3_benchmark_gemini_35_lite_20261025_165427_corrected.json`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/reports/scored_phase3_benchmark_gemini_35_lite_20261025_165427_corrected.json)
  - Llama: [`backend/evaluation/reports/scored_phase3_benchmark_llama32_20261025_173645.json`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/reports/scored_phase3_benchmark_llama32_20261025_173645.json)
- **Exported Final Audit CSV Summaries:**
  - Cohort & Categories: [`backend/evaluation/reports/summary_phase3_final_audit_cohort_and_categories_20261025.csv`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/reports/summary_phase3_final_audit_cohort_and_categories_20261025.csv)
  - Model Comparison: [`backend/evaluation/reports/summary_phase3_final_audit_model_comparison_20261025.csv`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/reports/summary_phase3_final_audit_model_comparison_20261025.csv)
- **Audit Verification Harness:** [`backend/evaluation/audit_phase3_verification.py`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/evaluation/audit_phase3_verification.py)
- **Regression Test Suite:** [`backend/tests/test_evaluation_phase3_dataset_and_fixture.py`](file:///E:/avadhesh/projects/Design%20Project/Design-Project/backend/tests/test_evaluation_phase3_dataset_and_fixture.py) (21 passed)
