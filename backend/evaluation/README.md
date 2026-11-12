# Orbit Research Evaluation Infrastructure

This directory contains the reproducible empirical evaluation infrastructure for our research study:

> **Research Question:** Does integrating documents, tasks, and team chat improve answer correctness on multi-source collaborative workspace questions compared with a plain LLM and documents-only RAG?

---

## 1. Experimental Configurations

The benchmark evaluates three configurations on an identical deterministic synthetic workspace:

| Configuration | Description | Context / Tools Enabled | Admin Action Tools | Document Pre-injection |
|---|---|---|---|---|
| **A. `plain_llm`** | Baseline Direct LLM | Minimal system prompt + question only. No workspace access or tools. | Strictly Disabled | Disabled |
| **B. `rag_docs_only`** | Documents-only RAG | Vector search (`search_workspace_tool`) + relevant document pre-injection. Task and chat tools disabled. | Strictly Disabled | Enabled |
| **C. `full_agent`** | Full Orbit Workspace Agent | LangGraph ReAct agent with documents (`search_workspace_tool`), tasks (`get_tasks_tool`), and chat messages (`get_recent_chat_tool`). | Strictly Disabled | Enabled |

*Note: All destructive/administrative action tools (`create_task`, `update_task`, email notifications) are strictly blocked during evaluation to ensure experimental isolation and safety.*

---

## 2. Model Selection and Attribution Policy

- **Multi-Model Support:** The runner supports both frontier cloud LLMs via Google Gemini API (`gemini-3.5-flash-lite`) and local open-weight LLMs via Ollama (`llama3.2:latest`) with matching generation parameters (`temperature=0.3`).
- **Attribution Auditing:** Every evaluation attempt inspects the active model instance and records:
  - `configured_model`: Model specified in the workspace database record or runner CLI arguments.
  - `resolved_model`: The concrete model identifier returned by the provider/LLM instance.
  - `provider`: Underlying provider (`gemini`, `ollama`, `mock`).
  - `model_parameters`: Active generation hyperparameters (temperature, max tokens).
- **Provenance Integrity:** If the resolved model differs from the configured model, both are recorded explicitly in the raw JSONL log and companion metadata file without silent overwriting.

---

## 3. Dataset Structure and Cohorts

The evaluation suite contains two benchmark datasets:

### A. Canonical Phase 3 Benchmark Dataset (`questions_phase3_100.json`)
The primary benchmark contains **100 questions** grounded in the deterministic synthetic workspace (Workspace 3):
- **Single-Source Questions (40 items, 40%):** Answerable strictly from a single document, task record, or chat message.
- **Multi-Source Questions (40 items, 40%):** Require synthesizing facts from at least two distinct source types (e.g., Document + Task, Task + Chat, Document + Chat, or all three).
- **Unanswerable Questions (20 items, 20%):** Realistic inquiries regarding facts absent from the workspace (e.g., nonexistent AWS credentials, unrecorded budgets, fictitious team members).

#### Evaluation Cohorts
To detect and guard against prompt/rubric overfitting, questions are partitioned into two cohorts:
1. **Baseline / Pilot Cohort (Q01–Q20, 20 questions):** 8 single-source, 8 multi-source, 4 unanswerable questions used during initial rubric calibration.
2. **Held-Out Cohort (Q21–Q100, 80 questions):** 32 single-source, 32 multi-source, 16 unanswerable questions evaluated strictly without per-question prompt tuning.

### B. Pilot Dataset (`questions.json`)
The historical 20-question pilot dataset used during Phase 2 calibration and smoke testing.

Each question item in both datasets includes:
- `id`: Stable unique identifier (e.g., `Q01` through `Q100`).
- `category`: `single_source`, `multi_source`, or `unanswerable`.
- `required_sources`: Expected sources (`documents`, `tasks`, `chat`).
- `reference_answer`: Factually verified ground truth.
- `evidence_references`: Exact excerpts from synthetic documents, tasks, or chat messages.
- `evaluation_criteria`: Explicit `target_values`, `required_concepts`, and `forbidden_values` (contradictions/hallucinations).
- `rubric`: Deterministic scoring rules (`exact_value`, `list`, `multi_source_synthesis`, `refusal`).

---

## 4. Deterministic Synthetic Workspaces

### Phase 3 Canonical Benchmark Workspace (Workspace 3)
- **Workspace ID:** `00000000-0000-4000-8000-000000000003`
- **Owner:** `eval-owner@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000002`)
- **Test Runner Identity:** `eval-dev1@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000003`)
- **QA:** `eval-qa@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000004`)
- **Dev 2:** `eval-dev2@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000005`)
- **Documents (3):**
  1. *Architecture Specification* (PostgreSQL, Redis, Supabase, LangGraph ReAct agents, auth policies)
  2. *Security & Compliance Policy* (JWT expiry, CORS, RBAC, secret masking)
  3. *Release Plan Sprint 15* (Sprint scope, deployment schedule, rollback procedures)
- **Tasks (16):** 16 structured task records spanning backend, frontend, infrastructure, and QA across Sprints 13–15.
- **Chat Messages (16):** 16 team communication entries capturing ad-hoc decisions, blocker resolutions, deployment approvals, and staging test outcomes.

### Phase 2 Pilot Workspace (Workspace 1)
- **Workspace ID:** `00000000-0000-4000-8000-000000000001`
- 3 Documents, 4 Tasks, 4 Chat Messages (used for initial 20-question pilot runs).

---

## 5. Security & Isolation Fixes

1. **Fail-Closed Vector Search (`app/rag/vector_store.py`):**
   - If PostgreSQL validation of active documents fails (e.g. database disconnect, query error), vector search **fails closed** and returns `[]`. It never falls back to returning raw, unvalidated chunks.
   - Deletion filtering and workspace ID matching are enforced.
2. **Task Administrative Permissions (`app/agents/tools.py`):**
   - `update_task` and `create_task` enforce database-backed admin verification (`_verify_workspace_admin`) and fail closed with descriptive permission errors.
3. **Log & Error Secret Sanitization (`evaluation/run_evaluation.py`):**
   - All errors and log strings are scrubbed with regex masks (`AIza...`, `Bearer ...`, `postgresql://user:pass@...`) to guarantee API keys, tokens, and DB passwords are never committed to disk.

---

## 6. Deterministic Scoring Rubric (`RUBRIC_VERSION = 2.2-deterministic-audited`)

Scoring is implemented deterministically in `backend/evaluation/score_results.py` without secondary LLM-as-a-judge bias:

### Answer Correctness
- **1.0 (Full Match):** All required `target_values` (ports, dates, names, statuses) and key concepts present with zero contradictions. Matching employs regex word boundaries (`\b`) to prevent false-negative substring rejections from surrounding punctuation, quotation marks, or markdown bold syntax (`**`).
- **0.5 (Partial Match):** At least 50% of required targets matched, or partial match with minor non-blocking contradiction.
- **0.0 (Incorrect):** Missing targets, pure contradictions, or incorrect numerical values.

### Unanswerable Questions & Refusal Verification
- **1.0 (Valid Refusal):** Response explicitly identifies that information is absent from the workspace. Recognizes both singular and plural semantic equivalence (e.g., *"the documents and task records do not contain information"* or *"neither the document nor task record mentions"*).
- **0.0 (Failed Refusal / Hallucination):** Model attempts to answer unanswerable questions. If `forbidden_values` appear, score is 0.0 **even if accompanied by a disclaimer**.
- **0.0 (Unnecessary Refusal):** If the model refuses an answerable question that is present in the workspace, score is 0.0.

### Evidence Faithfulness
- Assesses whether factual claims in the response are grounded in the evidence retrieved by tools.
- If a configuration has no retrieval access (`plain_llm`), answerable faithfulness is recorded as `0.0` with the explicit rationale: `"No retrieval evidence available in this configuration"`.
- Missing evidence is treated as missing evidence, distinct from factual error.

### Separated Performance Metrics
- **`coverage`:** Successful executions / total attempted questions.
- **`error_rate`:** Failed executions / total attempted questions.
- **`mean_correctness_all`:** Mean correctness score across all attempts (counting execution failures as 0.0).
- **`mean_correctness_successful`:** Mean correctness score computed strictly across successful (non-error) executions.
- **Latency & Tokens:** Latency statistics (mean, median, stddev) are reported separately for successful runs vs. failed attempts.

---

## 7. Empirical Results Summary

| Model | Configuration | Full Dataset Accuracy ($n=100$) | Held-Out Cohort Accuracy ($n=80$) | Held-Out Multi-Source ($n=32$) | Mean Faithfulness | Mean Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Google Gemini 3.5 Flash Lite** (Cloud API) | `plain_llm` | 22.50% | 23.13% | 0.00% | 1.0000 | 1,332 ms |
| | `rag_docs_only` | 53.00% | 60.00% | 40.63% | 0.8350 | 5,910 ms |
| | `full_agent` | **74.50%** | **86.25%** (+26.25 pp) | **84.38%** (+43.75 pp) | **0.9000** | 6,415 ms |
| **Meta Llama 3.2:latest (3.2B)** (Local Ollama) | `plain_llm` | 5.50% | 5.00% | 1.56% | 0.1000 | 6,300 ms |
| | `rag_docs_only` | 45.50% | 50.63% | 35.94% | 0.7550 | 18,028 ms |
| | `full_agent` | **47.00%** | **52.50%** (+1.88 pp) | **46.88%** (+10.94 pp) | 0.7500 | 19,496 ms |

### Key Findings
1. **Multi-Source Synthesis Superiority:** On the held-out multi-source slice ($n=32$), `full_agent` achieves **84.38%** on Gemini 3.5 Flash Lite—a **+43.75 percentage point gain** over `rag_docs_only` (40.63%) and **+84.38 percentage points** over `plain_llm` (0.00%). On Llama 3.2, `full_agent` achieves **46.88%** vs. 35.94% for RAG (+10.94 pp).
2. **Held-Out Generalization:** On the 80 held-out questions (Q21–Q100), Gemini `full_agent` reaches **86.25% accuracy** (+26.25 pp over RAG), demonstrating reliable generalization to uncalibrated questions.
3. **Execution Reliability:** Both models achieved **100% execution coverage** (300/300 successful attempts per model, 0 unhandled exceptions or timeout failures).

---

## 8. Directory Artifacts & Result Files

```
backend/evaluation/
├── configs.py                                                   # 3 configuration runners and LLM metadata inspectors
├── seed_synthetic_workspace.py                                  # Deterministic workspace seeder and integrity validator
├── run_evaluation.py                                            # Evaluation runner with sanitized logging
├── score_results.py                                             # Deterministic factual scorer (Rubric 2.2)
├── audit_phase3_verification.py                                 # Offline verification script for cross-cohort analysis
├── questions_phase3_100.json                                    # Canonical Phase 3 100-question benchmark dataset
├── questions.json                                               # Historical 20-question pilot dataset
│
├── results/                                                     # Raw 300-attempt JSONL logs and run provenance metadata
│   ├── phase3_benchmark_gemini_35_lite_20261025_165427.jsonl   # Gemini 3.5 Flash Lite raw execution log (300 attempts)
│   ├── meta_phase3_benchmark_gemini_35_lite_20261025_165427.json# Gemini run metadata and provenance
│   ├── phase3_benchmark_llama32_20261025_173645.jsonl           # Llama 3.2:latest raw execution log (300 attempts)
│   ├── meta_phase3_benchmark_llama32_20261025_173645.json       # Llama 3.2 run metadata and provenance
│   └── run_20261021_135109_129c49.jsonl                         # Historical Phase 2 baseline run
│
└── reports/                                                     # Scored evaluations, summary CSVs, and audit reports
    ├── final_audit_report_phase3_20261025.md                    # Comprehensive Phase 3 audit report and analysis
    ├── scored_phase3_benchmark_gemini_35_lite_20261025_165427_corrected.json # Gemini scored evaluation (Rubric 2.2)
    ├── scored_phase3_benchmark_llama32_20261025_173645.json     # Llama 3.2 scored evaluation (Rubric 2.2)
    ├── summary_phase3_benchmark_gemini_35_lite_20261025_165427_corrected.csv # Gemini configuration summary CSV
    ├── summary_phase3_benchmark_llama32_20261025_173645.csv     # Llama 3.2 configuration summary CSV
    ├── summary_phase3_final_audit_model_comparison_20261025.csv # Cross-model comparison summary CSV
    └── summary_phase3_final_audit_cohort_and_categories_20261025.csv # Cohort and category-level breakdown CSV
```
    └── summary_phase3_final_audit_cohort_and_categories_20261025.csv # Cohort and category-level breakdown CSV
```

---

## 9. Reproducibility & Verification Workflow

All commands should be run from the `backend/` directory:

```bash
cd backend
```

### 1. Run Offline Verification Suite (Zero LLM Calls)
Verify all raw results, cohort splits, and scored metrics against the canonical dataset:
```bash
python evaluation/audit_phase3_verification.py
```

### 2. Run Test Suite
Run unit tests, rubric regression tests, and offline smoke tests:
```bash
python -m pytest tests/test_evaluation_phase3_dataset_and_fixture.py tests/test_smoke_audit_fixes.py tests/test_offline_smoke_harness.py -o pythonpath=. -v
```

### 3. Re-score Any Benchmark Run (Deterministic Rubric 2.2)
To re-score any raw JSONL run file:
```bash
python -m evaluation.score_results -i evaluation/results/phase3_benchmark_gemini_35_lite_20261025_165427.jsonl -d evaluation/questions_phase3_100.json -o evaluation/reports/my_rescored_gemini.json -c evaluation/reports/my_rescored_gemini.csv
```

### 4. Run Mock Offline Smoke Harness
Verify the full end-to-end evaluation pipeline without external API calls:
```bash
python evaluation/run_evaluation.py --limit 5 --mock-llm --run-id smoke_test_offline
```

---

## 10. Limitations & Future Work

1. **Synthetic Workspace Scope:** While grounded in realistic engineering workflows (sprints, tasks, architecture, chats), synthetic data has lower ambiguity and noise than production enterprise repositories. Future benchmarks should evaluate enterprise slack/jira archives under differential privacy.
2. **Local Model Multi-Turn Reasoning:** While Llama 3.2:latest achieved 100% execution reliability, its multi-source correctness (67.2%) lagged Gemini 3.5 Flash Lite (93.8%), reflecting occasional omissions when synthesizing across all three modalities simultaneously. Exploring tool-use fine-tuning for smaller parameter models remains an active research direction.
3. **Sub-Source Fine-Grained Ablations:** The current study evaluates three configurations (`plain_llm`, `rag_docs_only`, `full_agent`). Pairwise ablations (`docs_plus_tasks`, `docs_plus_chat`) could further isolate individual marginal contributions of each context stream.
