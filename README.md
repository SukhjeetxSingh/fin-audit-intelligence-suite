# 🛡️ Agentic AI for Financial Services — SAR Processing System

An end-to-end **Suspicious Activity Report (SAR)** automation pipeline built with a multi-agent architecture, Pydantic data validation, Chain-of-Thought reasoning, ReACT-based narrative generation, and a live Streamlit compliance dashboard.

The system ingests customer, account, and transaction data; screens it for suspicious financial activity; reasons through a classification using Chain-of-Thought prompting; routes high-risk cases through a human-in-the-loop review gate; and generates regulator-ready SAR narratives using a ReACT (Reasoning + Acting) agent — all while keeping a full audit trail of every decision.

---

## 🎯 What It Does

- **Detects suspicious financial activity** using AI-powered pattern recognition across customer, account, and transaction data
- **Classifies activity** into five typologies — `Structuring`, `Sanctions`, `Fraud`, `Money_Laundering`, `Other` — with confidence scores and risk levels
- **Generates regulatory-ready narratives** (≤120 words) suitable for FinCEN-style SAR filing, complete with regulatory citations
- **Implements a human-in-the-loop decision gate** before expensive narrative generation runs
- **Produces complete audit trails** of every agent decision for compliance review
- **Visualizes results** through an interactive Streamlit dashboard

---

## 🏗️ Architecture Overview

```
CSV Data → DataLoader → CaseData Objects
                              ↓
                    ┌─────────────────────┐
                    │  FraudOrchestrator  │
                    │  4-Agent Pipeline   │
                    └─────────────────────┘
                         ↓         ↓
               TriageAgent    RiskAnalystAgent
               (Screening)    (Chain-of-Thought)
                         ↓         ↓
            StructuringExpert  ComplianceOfficerAgent
            (Pattern Analysis) (ReACT + Narrative)
                              ↓
                    SAR Document + Audit Log
                              ↓
                    Streamlit Dashboard
```

The pipeline runs in two stages:

1. **Risk Screening & Analysis** — cases are filtered by risk rating and activity volume, then passed through Triage and Risk Analyst agents for an initial Chain-of-Thought classification.
2. **Human Review → Compliance Narrative** — only cases that clear human review proceed to the Compliance Officer agent, which drafts and validates the final SAR narrative using a ReACT loop. This keeps the more expensive narrative-generation calls limited to approved cases.

---

## 📁 Project Structure

```
.
├── app.py                          # Streamlit SAR workflow dashboard
├── requirements.txt                # All dependencies
│
├── config/
│   ├── models.yaml                 # Model tier configuration
│   ├── pipeline_config.yaml        # Directory paths + pipeline settings
│   └── prompts.yaml                # Agent system prompts
│
├── data/
│   ├── customers.csv               # Synthetic customer records
│   ├── accounts.csv                # Account data
│   └── transactions.csv            # Transaction history
│
├── notebooks/
│   ├── 01_data_exploration.ipynb   # Data exploration + schema validation
│   ├── 02_agent_development.ipynb  # Agent development + testing
│   ├── 03_workflow_integration.ipynb  # Two-stage workflow integration
│   └── demo_automated_pipeline.ipynb  # End-to-end automated pipeline run
│
├── outputs/
│   ├── audit_logs/                 # JSONL audit trails for each pipeline run
│   ├── charts/                     # Workflow visualization PNGs
│   ├── filed_sars/                 # Individual SAR JSON documents
│   └── live_dashboard/             # Data consumed by the Streamlit dashboard
│
├── src/
│   ├── foundation_sar.py           # Pydantic schemas + DataLoader + ExplainabilityLogger
│   ├── base_agent.py               # BaseAgent base class
│   ├── triage_analyst_agent.py     # TriageAgent — initial case screening
│   ├── risk_analyst_agent.py       # RiskAnalystAgent — Chain-of-Thought analysis
│   ├── structuring_expert.py       # StructuringExpert — pattern detection
│   ├── compliance_officer_agent.py # ComplianceOfficerAgent — ReACT narrative
│   ├── orchestrator.py             # FraudOrchestrator — pipeline coordinator
│   ├── config_manager.py           # Loads models.yaml + prompts.yaml
│   ├── demo_integration_pipeline.py# Workflow helper functions
│   ├── test_scenarios.py           # Test case scenarios
│   └── mock/
│       ├── mock_client.py          # InternalMockClient — runs without API cost
│       └── mock_agent_output.py    # Mock agent response fixtures
│
└── tests/
    ├── test_foundation.py          # Pydantic schema + DataLoader tests
    ├── test_risk_analyst.py        # RiskAnalystAgent unit tests
    └── test_compliance_officer.py  # ComplianceOfficerAgent unit tests
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- An OpenAI API key
- (Recommended) VS Code with the Jupyter extension

### Installation

#### 🛠️ Environment Setup & Quickstart

If you are working directly from the repository root directory, execute this single command chain to initialize your isolated virtual environment, activate it, and install all project dependencies:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade -r requirements.txt
```

> **_NOTE:_** If your terminal opens outside of the repository's root directory, navigate into your workspace folder by running the sequence below:
```
cd fin-audit-intelligence-suite && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```
> **_NOTE:_** If your terminal opens outside of the repository's root directory, navigate into your workspace folder by running the sequence below:
> Make sure to replace `fin-audit-intelligence-suite` with your actual `YOUR_ROOT_DIRECTORY_NAME` if your repository folder is named differently.


# Set up environment variables
cp .env.template .env
```

Edit `.env` and add your API key:

```
OPENAI_API_KEY=your_actual_api_key_here
```

### Running the Pipeline

Run the first cell of `demo_automated_pipeline.ipynb` each session to ensure dependencies are present:

```python
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"], check=True)
```

Then open and run all cells in:

```
notebooks/demo_automated_pipeline.ipynb
```

### Launching the Dashboard

```bash
streamlit run app.py
```

---

## ⚙️ Configuration

`config/pipeline_config.yaml` controls all directory paths and pipeline settings — output paths resolve consistently regardless of the directory the pipeline is launched from. `config/models.yaml` defines model tiers, and `config/prompts.yaml` holds the agent system prompts.

### Mock vs. Real API Mode

The pipeline can run with or without live API calls, controlled by a single flag at the top of the main notebook:

```python
USE_MOCK = True   # default — InternalMockClient returns deterministic responses, no API cost
USE_MOCK = False  # routes through the real OpenAI client, requires a valid OPENAI_API_KEY
```

In mock mode, `InternalMockClient` returns deterministic responses based on transaction patterns — every pipeline stage runs, SAR documents are generated, and the dashboard works fully, which makes it well suited for development and demos. In real-API mode, the orchestrator pauses on any case flagged `HUMAN_REVIEW` so a person can review it before the (more expensive) compliance narrative step runs.

| Mode | Relative cost per case | Typical use |
|---|---|---|
| Mock (`USE_MOCK=True`) | None | Development, testing, demos |
| Real API (`USE_MOCK=False`) | Screening + narrative generation calls | Production runs |

---

## 📐 Foundation & Data Modeling

### Pydantic Schemas (`src/foundation_sar.py`)

| Schema | Purpose | Key Fields |
|---|---|---|
| `CustomerData` | Customer profile | `customer_id`, `name`, `risk_rating` (Low/Medium/High), `customer_since` (date) |
| `AccountData` | Account details | `account_id`, `customer_id`, `balance` (float), `account_type` |
| `TransactionData` | Transaction record | `transaction_id`, `amount` (float), `transaction_date` (date), `transaction_type` |
| `CaseData` | Unified case object | Links customer + accounts + transactions with a unique `case_id` |
| `RiskAnalystOutput` | Risk assessment result | `classification`, `confidence_score` (0.0–1.0), `risk_level`, `key_indicators` |
| `ComplianceOfficerOutput` | SAR narrative | `narrative`, `regulatory_citations`, `completeness_check` |

**Validation rules:**
- `risk_rating` constrained to `['Low', 'Medium', 'High']`
- `confidence_score` bounded `0.0–1.0`
- `risk_level` constrained to `['Low', 'Medium', 'High', 'Critical']`
- `classification` constrained to `['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other']`
- Date fields parsed with `datetime` validators
- Optional fields default to `None` or `[]` to handle missing CSV values

### DataLoader & ExplainabilityLogger

- **`DataLoader`** — merges `customers.csv`, `accounts.csv`, and `transactions.csv` into unified `CaseData` objects via `create_case_from_data()`
- **`ExplainabilityLogger`** — writes structured JSONL audit entries with timestamps, unique identifiers, agent decisions, and reasoning chains

---

## 🔍 Risk Analyst Agent — Chain-of-Thought

**File:** `src/risk_analyst_agent.py`

`RiskAnalystAgent` uses a Chain-of-Thought system prompt that enforces step-by-step reasoning before classification:

```
Step 1: Identify transaction patterns (velocity, amounts, timing)
Step 2: Check for threshold structuring indicators ($8,000–$9,999 band)
Step 3: Assess counterparty and geographic risk
Step 4: Evaluate against known typologies
Step 5: Assign classification and confidence score
```

**Supported classifications:**

| Classification | Trigger Pattern |
|---|---|
| `Structuring` | Repeated transactions just below the $10K CTR threshold |
| `Sanctions` | Counterparty matches watchlist indicators |
| `Fraud` | Unusual account takeover or identity patterns |
| `Money_Laundering` | Layering — high-velocity in/out wire transfers |
| `Other` | Suspicious but doesn't fit the above typologies |

**Output:** a `RiskAnalystOutput` containing `confidence_score` (0.0–1.0), `risk_level` (Low/Medium/High/Critical), and a `key_indicators` list.

**Error handling:** JSON parsing failures fall back to `_generate_fallback_analysis()` with a structured response; API errors are caught and logged so the pipeline continues rather than crashing.

---

## ⚖️ Compliance Officer Agent — ReACT Framework

**File:** `src/compliance_officer_agent.py`

`ComplianceOfficerAgent` implements a ReACT (Reasoning + Acting) loop:

```
REASON → Analyze the risk findings and determine regulatory obligations
ACT    → Draft the SAR narrative with required elements
REASON → Verify narrative completeness against a BSA/AML-style checklist
ACT    → Add regulatory citations and finalize for submission
```

**Narrative requirements:**
- ≤ 120 words (enforced in the system prompt and validated post-generation)
- Covers who (subject), what (activity), when (timeframe), where (accounts/locations), and why (basis for suspicion)
- Professional tone suitable for regulatory submission
- Includes regulatory citations (e.g., `31 CFR 1020.320`, `BSA 31 U.S.C. 5318(g)`)

**Output:** a `ComplianceOfficerOutput` containing `narrative`, `narrative_reasoning`, `regulatory_citations`, and `completeness_check`.

---

## 🔄 Two-Stage Workflow

**File:** `src/demo_integration_pipeline.py` (invoked from `demo_automated_pipeline.ipynb`)

### Stage 1 — Risk Screening

```python
selected_customers, rest_of_cases = screen_high_risk_customers(
    customers_data, accounts_data, transactions_data
)
```

Screening criteria: `risk_rating` in `['Medium', 'High']` **and** (`total_amount > $100K` **or** `transaction_count > 50`).

### Stage 2 — 4-Agent Escalation Pipeline

```python
res1 = run_agent_pipeline(high_risk_cases, orchestrator, is_high_risk=True)
```

```
Triage → Risk Analyst → Structuring Expert → Compliance Officer
  ↓            ↓                ↓                    ↓
Filter      CoT Analysis    Pattern Check      ReACT Narrative
```

Cases flagged `HUMAN_REVIEW` pause the pipeline for manual review before the (costlier) narrative-generation step runs.

---

## 📄 SAR Document Structure

Each approved case generates a JSON file under `outputs/filed_sars/`:

```json
{
  "sar_metadata":        { "sar_id", "filing_date", "ai_generated", "review_status" },
  "subject_information": { "customer_name", "customer_id", "risk_rating", "customer_since" },
  "suspicious_activity": { "classification", "risk_level", "confidence_score",
                           "narrative", "key_indicators", "ai_reasoning" },
  "regulatory_compliance": { "citations", "narrative_word_count", "compliance_status" },
  "audit_trail":         { "case_id", "processing_date", "ai_agents_used", "human_reviewer" }
}
```

---

## 📊 Audit Trail & Efficiency Metrics

Every agent decision is written to `outputs/audit_logs/` as JSONL:

```json
{
  "case_id": "...", "customer_name": "...", "decision": "PROCEED",
  "ai_classification": "Money_Laundering", "ai_confidence": 0.91,
  "compliance_narrative_exists": true, "timestamp": "..."
}
```

`analyze_workflow_efficiency()` prints a summary of pipeline cost, time savings versus a manual baseline, and the share of cases meeting a high-confidence threshold.

---

## 📈 Live Dashboard (`app.py`)

Launch with `streamlit run app.py`.

| Tab | Contents |
|---|---|
| 📊 Overview | Filing volume timeline, classification mix, data quality notes |
| 🏷️ Classification & Confidence | Distribution charts, risk level breakdown, confidence histograms |
| 💰 Workflow Economics | Interactive what-if cost/ROI calculator |
| 🤖 AI Decision Analytics | Agent roster, override tracking, top flagged customers |
| 🔎 Case Explorer | Search by customer/SAR ID, full narrative drill-down, CSV export |
| 🟢 Latest Run | Current batch summary, per-case decisions, transaction drill-down |

Data sources (all under `outputs/live_dashboard/`): `sar_history.csv` (aggregated historical SAR records), `sar_history_meta.json` (load stats and failure counts), and `live_session.json` (current run case data).

---

## 🧪 Testing

The project includes **30 tests** across three modules.

```bash
# Run all tests
python -m pytest tests/ -v

# Run individual module tests
python -m pytest tests/test_foundation.py -v          # Core data structures
python -m pytest tests/test_risk_analyst.py -v         # Chain-of-Thought agent
python -m pytest tests/test_compliance_officer.py -v   # ReACT agent

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

| Module | Tests | Coverage |
|---|---|---|
| `test_foundation.py` | 10 | Schema validation, CSV loading, case aggregation, audit logging |
| `test_risk_analyst.py` | 10 | Agent initialization, case analysis, JSON parsing, error handling |
| `test_compliance_officer.py` | 10 | Narrative generation, word-limit enforcement, citations, multi-format parsing |

---

## 🔍 Troubleshooting & Lessons Learned

- **Path resolution** — output files were inconsistently written depending on the launch directory; resolved by anchoring all paths to `__file__` in `demo_integration_pipeline.py` and `app.py`.
- **CSV vs. Parquet** — `pyarrow` version conflicts caused errors when saving list-type columns (`key_indicators`, `ai_agents_used`, `citations`); switched to CSV with `ast.literal_eval()` parsing on read to restore list types.
- **API response variability** — agents occasionally returned malformed JSON or unsupported `classification` values; mitigated with a fallback in `run_agent_pipeline()` that remaps unrecognized classifications to `'Other'`.
- **Logger compatibility** — some agents called `self.logger.info()`, which `ExplainabilityLogger` doesn't implement; replaced with `print()` in the affected agent files.

---

## 📦 Dependencies

```
pandas          # data manipulation
pydantic        # schema validation
openai          # LLM API client
python-dotenv   # environment variables
streamlit       # dashboard
plotly          # interactive charts
matplotlib      # workflow visualization charts
pyyaml          # config file loading
jupyter         # notebook environment
pytest          # testing framework
```

Install everything at once:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Built With

* [Python](https://python.org) — core language
* [Pydantic](https://pydantic-docs.helpmanual.io/) — data validation and settings management
* [OpenAI API](https://platform.openai.com/) — LLM integration
* [Pandas](https://pandas.pydata.org/) — data manipulation and analysis
* [Jupyter](https://jupyter.org/) — interactive development environment
* [pytest](https://pytest.org/) — testing framework
* [python-dotenv](https://pypi.org/project/python-dotenv/) — environment variable management
* [Streamlit](https://streamlit.io/) — live dashboard
* [Plotly](https://plotly.com/) — interactive charts
* [Matplotlib](https://matplotlib.org/) — data visualization

**Methodologies:** Chain-of-Thought prompting, ReACT (Reasoning + Acting) prompting, multi-agent architecture, human-in-the-loop review.

---

## ⚠️ Note

This project uses synthetic financial data for demonstration purposes. It illustrates AI-assisted detection and reporting techniques and is not a substitute for a production-grade regulatory compliance system.
