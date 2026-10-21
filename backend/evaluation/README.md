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

- **Standardization:** All three configurations use the workspace's configured model (`gemini-3.5-flash-lite` by default in live runs, or `mock-eval-model` in offline mode) with matching generation parameters (`temperature=0.3`).
- **Attribution Auditing:** Every evaluation attempt inspects the active model instance to record both:
  - `configured_model`: Model specified in the workspace database record or environment.
  - `resolved_model`: The concrete model identifier returned by the provider/LLM instance.
  - `provider`: Underlying provider (`gemini`, `ollama`, `mock`).
  - `model_parameters`: Active generation hyperparameters (temperature).
- **No Discrepancy Masking:** If the resolved model differs from the configured model, both are recorded explicitly in the raw JSONL log without silent overwriting.

---

## 3. Dataset Structure and Grounding

The evaluation dataset (`backend/evaluation/questions.json`) consists of **20 questions** grounded in the synthetic workspace:

- **Single-Source Questions (8 items, Q01–Q08):** Answerable strictly from a single document, task record, or chat message.
- **Multi-Source Questions (8 items, Q09–Q16):** Require synthesizing facts from at least two distinct source types (e.g. Document + Task, Task + Chat, Document + Chat).
- **Unanswerable Questions (4 items, Q17–Q20):** Realistic inquiries regarding facts absent from the workspace (e.g., nonexistent AWS keys, unrecorded budgets, team members in Madrid).

Each question includes:
- `id`: Stable unique identifier (e.g., `Q01`).
- `category`: `single_source`, `multi_source`, or `unanswerable`.
- `required_sources`: Expected sources (`documents`, `tasks`, `chat`).
- `reference_answer`: Factually verified ground truth.
- `evidence_references`: Exact excerpts from synthetic documents, tasks, or chat messages.
- `evaluation_criteria`: Explicit `target_values`, `required_concepts`, and `forbidden_values` (contradictions/hallucinations).
- `rubric`: Deterministic scoring rules (`exact_value`, `list`, `multi_source_synthesis`, `refusal`).

---

## 4. Deterministic Synthetic Workspace

The synthetic workspace fixture (`backend/evaluation/seed_synthetic_workspace.py`) uses deterministic UUIDs:
- **Workspace ID:** `00000000-0000-4000-8000-000000000001`
- **Owner:** `eval-owner@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000002`)
- **Dev 1 (Test Runner Identity):** `eval-dev1@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000003`)
- **QA:** `eval-qa@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000004`)
- **Dev 2:** `eval-dev2@synthetic.orbit.local` (`00000000-0000-4000-8000-000000000005`)
- **Documents (3):** Architecture Spec, Security Policy, Sprint 14 Release Plan.
- **Tasks (4):** Redis connection pool, OAuth token refresh, Auth e2e tests, Database index audit.
- **Chat Messages (4):** Team standup notes and confirmations in Supabase `messages`.

### Seeding Safety & Cleanup Scope
- Seeding **only** modifies records associated with `SYNTHETIC_WORKSPACE_ID` and the synthetic user identities.
- Purges existing records from PostgreSQL (`tasks`, `documents`, `workspace_members`, `workspaces`) and Supabase (`embeddings`, `messages`) before inserting clean deterministic records.
- Stale vector chunks from previous seedings are explicitly deleted from Supabase `embeddings` to prevent chunk contamination.

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

## 6. Deterministic Scoring Rubric (`RUBRIC_VERSION = 2.0-deterministic-factual`)

Scoring is handled by `backend/evaluation/score_results.py`:

### Answer Correctness
- **1.0 (Full Match):** All required `target_values` (ports, dates, names, statuses) and key concepts present with zero contradictions.
- **0.5 (Partial Match):** At least 50% of required targets matched, or partial match with minor contradiction.
- **0.0 (Incorrect):** Missing targets, pure contradictions, or wrong numerical values.

### Unanswerable Questions & Refusal Verification
- **1.0 (Valid Refusal):** Response explicitly identifies that information is missing from the workspace and does **not** hallucinate forbidden facts.
- **0.0 (Failed Refusal / Hallucination):** Model attempts to answer unanswerable questions. If `forbidden_values` (e.g. fabricated AWS access keys or budgets) appear, score is 0.0 **even if accompanied by a disclaimer**.
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
- **Latency & Tokens:** Latency statistics (mean, median, stddev) are reported separately for successful runs vs failed attempts.

---

## 7. Step-by-Step Workflow & Commands

All commands must be run from the `backend/` directory:

```bash
cd backend
```

### 1. Run All Tests
Execute unit tests, vector search fail-closed tests, attribution tests, and mock end-to-end checks:
```bash
python -m pytest tests/ -v
```

### 2. Seed the Synthetic Workspace Fixture
Seed the deterministic workspace fixture:
```bash
python -m evaluation.seed_synthetic_workspace
```
*To verify workspace and vector integrity without re-seeding:*
```bash
python -m evaluation.seed_synthetic_workspace --verify
```
*To seed relational data without generating embeddings:*
```bash
python -m evaluation.seed_synthetic_workspace --skip-embeddings
```

### 3. Run Mock Smoke Test (Offline, Zero Cost)
Verify runner execution across all 3 configurations on the first 5 questions using the mock LLM:
```bash
python evaluation/run_evaluation.py --limit 5 --mock-llm --run-id smoke_test_offline
```

### 4. Run Live Smoke Test (Gemini API)
Verify live LLM connections and tool calling on the first 5 questions (15 attempts total):
```bash
python evaluation/run_evaluation.py --limit 5 --run-id smoke_test_live
```

### 5. Run Full 20-Question Benchmark
Execute the complete pilot across all 3 configurations (60 attempts total):
```bash
python evaluation/run_evaluation.py --run-id orbit_pilot_v1
```

### 6. Score Results and Generate Reports
Score any raw JSONL run file and output summary CSV and JSON reports:
```bash
python -m evaluation.score_results -i evaluation/results/<RUN_ID>.jsonl
```
Example for historical baseline:
```bash
python -m evaluation.score_results -i evaluation/results/run_20261021_135109_129c49.jsonl
```

### 7. Inspect Git Changes
Review all modifications against the clean baseline:
```bash
git diff
```

---

## 8. Directory Artifacts

```
backend/evaluation/
├── configs.py                    # 3 configuration runners and LLM metadata inspectors
├── seed_synthetic_workspace.py   # Deterministic workspace seeder and integrity validator
├── questions.json                # 20-question pilot dataset with explicit rubrics
├── run_evaluation.py             # Evaluation runner with sanitized logging
├── score_results.py              # Deterministic factual scorer (Rubric 2.0)
├── results/                      # Raw JSONL run files (append-only)
│   ├── run_20261021_135109_129c49.jsonl  # Historical smoke test baseline (preserved)
│   └── smoke_test_verified.jsonl         # Verified mock evaluation run
└── reports/                      # Derived summary CSVs and scored JSON files
    ├── summary_run_20261021_135109_129c49.csv
    ├── scored_run_20261021_135109_129c49.json
    ├── summary_smoke_test_verified.csv
    └── scored_smoke_test_verified.json
```

---

## 9. Limitations & Next Research Steps

1. **Pilot Dataset Size:** The 20-question dataset is designed as an internal pilot benchmark. Expanding to 60–100 questions with external human verification is recommended for statistical significance.
2. **Provider Rate Limits (429 RESOURCE_EXHAUSTED):** Quota exhaustion on free or tier-1 Gemini APIs requires pacing (e.g. 5–10s delay between agent turns) or moving to enterprise quotas. The runner preserves 429 errors without corrupting scored response metrics.
3. **Fine-Grained Ablations:** The current study tests `plain_llm`, `rag_docs_only`, and `full_agent` (docs + tasks + chat). Future work should include pairwise ablations (`docs_plus_tasks`, `docs_plus_chat`) to isolate causal contributions of individual context streams.
