# Orbit Research Evaluation Infrastructure

This directory provides the reproducible empirical evaluation infrastructure for the research question:

> **Does integrating documents, tasks, and team chat improve answer correctness on multi-source collaborative workspace questions compared with a plain LLM and documents-only RAG?**

---

## 1. Experimental Configurations

The evaluation runner compares three configurations against the identical question dataset and test identity:

| Configuration | Description | Available Context & Tools | Admin Actions | Pre-injection |
|---|---|---|---|---|
| **A. `plain_llm`** | Plain LLM Baseline | Direct chat prompt only. No workspace documents, tasks, chat, or tools. | None | Disabled |
| **B. `rag_docs_only`** | Documents-only RAG | Document retrieval tool (`search_workspace_tool`) and pre-injected relevant chunks. Tasks and chat tools strictly disabled. | None | Enabled |
| **C. `full_agent`** | Full Orbit Agent | LangGraph ReAct agent with documents (`search_workspace_tool`), tasks (`get_tasks_tool`), and chat (`get_recent_chat_tool`). | Disabled | Enabled |

*Note: All administrator action tools (`create_task`, `update_task`, email notifications) are disabled for ordinary evaluation runs.*

---

## 2. Directory Structure

```
backend/evaluation/
├── configs.py                    # Reusable definitions and execution handlers for the 3 configurations
├── seed_synthetic_workspace.py   # Deterministic fixture seeding isolated synthetic workspace data
├── questions.json                # Structured 20-question pilot benchmark dataset
├── run_evaluation.py             # Asynchronous evaluation runner with CLI switches and logging
├── score_results.py              # Transparent scoring rubric, latency stats, and CSV/JSON reporter
├── results/                      # Append-only raw JSONL execution traces (timestamped & uniquely named)
├── reports/                      # Derived CSV and JSON aggregate scoring reports
└── README.md                     # Documentation and workflow guide
```

---

## 3. Step-by-Step Workflow Commands

All commands should be executed from the `backend/` directory with the virtual environment activated:

```bash
cd backend
```

### Step 1: Run Regression Tests
Verify workspace authorization fixes, evaluation configuration filtering, and runner components:
```bash
python -m pytest tests/ -v
```

### Step 2: Seed the Isolated Synthetic Workspace
Seeds deterministic test workspace `00000000-0000-4000-8000-000000000001` with synthetic users, documents, tasks, and team chat. Never alters normal developer or production workspaces.
```bash
python -m evaluation.seed_synthetic_workspace
```

### Step 3: Run the 5-Question Smoke Test
Executes all 3 configurations on the first 5 questions (15 attempts total) to verify live API connections, source filtering, and logging:
```bash
python evaluation/run_evaluation.py --limit 5
```
*For offline testing without API credits or network access, append `--mock-llm`:*
```bash
python evaluation/run_evaluation.py --limit 5 --mock-llm
```

### Step 4: Run the Full 20-Question Pilot
Executes all 3 configurations on the full 20-question pilot benchmark (60 attempts total):
```bash
python evaluation/run_evaluation.py
```

### Step 5: Repeating a Run or Running Specific Configurations
To evaluate only a subset of configurations or assign a custom run ID:
```bash
python evaluation/run_evaluation.py --configs rag_docs_only,full_agent --run-id pilot_rerun_01
```

### Step 6: Score and Export Results
Compute correctness, evidence faithfulness, latency percentiles, token usage, and generate summary CSV/JSON reports:
```bash
python evaluation/score_results.py --input-file evaluation/results/<YOUR_RUN_FILE>.jsonl
```
Example:
```bash
python evaluation/score_results.py --input-file evaluation/results/run_20261021_135109_129c49.jsonl
```

---

## 4. Dataset Schema & Adding New Questions

The dataset is stored in `backend/evaluation/questions.json`.

### Schema Format

```json
{
  "id": "Q21",
  "question": "What is the deployment port and when was it verified?",
  "category": "multi_source",
  "required_sources": ["documents", "chat"],
  "reference_answer": "The backend port is 8000 from the architecture guide and chat confirmed verification.",
  "evidence_references": [
    {
      "source": "documents",
      "document_title": "Architecture and Deployment Specification",
      "excerpt": "The backend API runs on port 8000 using FastAPI."
    },
    {
      "source": "chat",
      "sender": "eval-qa@synthetic.orbit.local",
      "excerpt": "No regressions found on Safari or Chrome."
    }
  ],
  "answerable": true
}
```

### Guidelines for Expanding the Benchmark to 100 Questions:
1. **Maintain balanced allocation**:
   - Single-source: ~40% (documents, tasks, chat)
   - Multi-source: ~40% (documents + tasks, documents + chat, tasks + chat, documents + tasks + chat)
   - Unanswerable: ~20% (clearly out-of-scope or absent from workspace data)
2. **Ground in synthetic facts**: Never invent facts not present in the synthetic fixture. When adding questions requiring new facts, update `seed_synthetic_workspace.py` first.
3. **Validate before running**: Run `python -m pytest tests/test_evaluation_runner_and_scoring.py` to ensure schema integrity and unique IDs.

---

## 5. Scoring Rubric

- **Answerable Questions (`answerable: true`)**:
  - `1.0`: Key factual claims and entity references match the reference answer and evidence excerpts.
  - `0.5`: Partial factual coverage.
  - `0.0`: Missing critical information or incorrect facts.
- **Unanswerable Questions (`answerable: false`)**:
  - `1.0`: Correctly recognizes missing information and refuses fabrication.
  - `0.0`: Hallucinates answers or fabricates credentials/private data.
- **Evidence Faithfulness**:
  - Measures the ratio of cited evidence excerpts accurately represented in the response without contradiction.
- **Latency**:
  - Measured in milliseconds wall-clock time per question attempt.
- **Token Usage**:
  - Captured directly from provider response metadata when exposed (recorded as `null` if unavailable).
