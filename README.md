# 🛡️ Agentic AI for Financial Services — SAR Processing System

An end-to-end **Suspicious Activity Report (SAR)** automation pipeline built with a multi-agent architecture, Pydantic data validation, Chain-of-Thought reasoning, ReACT-based narrative generation, and a live Streamlit compliance dashboard.[file:233][file:236]

The system ingests customer, account, and transaction data; screens it for suspicious financial activity; reasons through a classification using Chain-of-Thought prompting; routes high-risk cases through a human-in-the-loop review gate; and generates regulator-ready SAR narratives using a ReACT (Reasoning + Acting) agent — all while keeping a full audit trail of every decision.[file:233][file:236]

---

## 🎯 What It Does

- **Detects suspicious financial activity** using AI-powered pattern recognition across customer, account, and transaction data  
- **Classifies activity** into five typologies — `Structuring`, `Sanctions`, `Fraud`, `Money_Laundering`, `Other` — with confidence scores and risk levels  
- **Generates regulatory-ready narratives** (≤120 words) suitable for FinCEN-style SAR filing, complete with regulatory citations  
- **Implements a human-in-the-loop decision gate** before expensive narrative generation runs  
- **Produces complete audit trails** of every agent decision for compliance review  
- **Visualizes results** through an interactive Streamlit dashboard[file:233][file:236]

---

## ✅ What’s New in This Implementation

- **4‑Agent Escalation Pipeline**: Triage, Risk Analyst, Structuring Expert, and Compliance Officer are coordinated by a `FraudOrchestrator`, with explicit stages and escalation logic.[file:238]  
- **AI-Only vs Human-Approved Flows**: SARs can be filed directly by the AI (`review_status="ai_only"`, `human_reviewer = null`) or via a human-reviewed path (`review_status="human_approved"`, `human_reviewer = "compliance_officer"`), captured in SAR JSONs and audit logs.[file:236]  
- **Deterministic Mock Mode**: An `InternalMockClient` plus a `USE_MOCK` flag allows full end-to-end runs with deterministic outputs and zero API cost.[file:236][file:238]  
- **Stable Output Pathing**: All outputs (SARs, logs, charts, dashboard data) resolve under `outputs/` via helpers in `demo_integration_pipeline.py`, independent of where the notebook or script is launched from.[file:236]  
- **Dashboard-Ready Aggregates & KPIs**: Helpers such as `aggregate_sar_history`, `export_live_session`, and `calculate_kpis` generate CSV, JSON, and KPI metrics consumed by the Streamlit dashboard.[file:236]  
- **Comprehensive Testing**: 30 tests cover foundation schemas, the RiskAnalystAgent, and the ComplianceOfficerAgent, plus integration and end-to-end workflow checks.[file:233]

---

## 🏗️ Architecture Overview

```text
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

The pipeline runs in two stages:[file:233][file:236]

1. **Risk Screening & Analysis** — cases are filtered by risk rating and activity volume, then passed through Triage and Risk Analyst agents for an initial Chain-of-Thought classification.  
2. **Human Review → Compliance Narrative** — only cases that clear human review proceed to the Compliance Officer agent, which drafts and validates the final SAR narrative using a ReACT loop; this keeps expensive narrative-generation calls limited to approved cases.[file:233][file:236]

---

## 📁 Project Structure

```text
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
[file:233][file:236][file:243]

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+  
- An OpenAI API key  
- (Recommended) VS Code with the Jupyter extension

### Installation

#### 🛠️ Environment Setup & Quickstart

From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade -r requirements.txt
```

If your terminal opens outside the repository root:

```bash
cd fin-audit-intelligence-suite \
  && python3 -m venv .venv \
  && source .venv/bin/activate \
  && pip install -r requirements.txt
```

(Replace `fin-audit-intelligence-suite` with your actual root directory name.)

#### Set up environment variables

```bash
cp .env.template .env
```

Edit `.env` and add your API key:

```text
OPENAI_API_KEY=your_actual_api_key_here
```

### Running the Pipeline

Run the first cell of `demo_automated_pipeline.ipynb` each session to ensure dependencies are present:

```python
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"], check=True)
```

Then open and run:

```text
notebooks/demo_automated_pipeline.ipynb
```
[file:233][file:236]

### Launching the Dashboard

```bash
streamlit run app.py
```
[file:236]

---

## ⚙️ Configuration

`config/pipeline_config.yaml` controls directory paths and pipeline settings; output paths resolve consistently under `outputs/` regardless of the directory the pipeline is launched from.[file:236]  
`config/models.yaml` defines model tiers, and `config/prompts.yaml` holds the agent system prompts.[file:247][file:246]

---

## 🧪 Mock vs Real API Mode

The pipeline can run with or without live API calls, controlled by a single flag at the top of the main notebook:

```python
USE_MOCK = True   # default — InternalMockClient returns deterministic responses, no API cost
USE_MOCK = False  # routes through the real OpenAI client, requires a valid OPENAI_API_KEY
```

In mock mode, `InternalMockClient` returns deterministic responses based on transaction patterns — every pipeline stage runs, SAR documents are generated, and the dashboard works fully.[file:236][file:238]  
In real-API mode, the orchestrator pauses on any case flagged `HUMAN_REVIEW` so a person can review it before the compliance narrative step runs.[file:238]

| Mode                        | Relative cost per case         | Typical use                     |
|-----------------------------|--------------------------------|---------------------------------|
| Mock (`USE_MOCK=True`)      | None                           | Development, testing, demos     |
| Real API (`USE_MOCK=False`) | Screening + narrative calls    | Production-like runs on sandbox |

---

## 📐 Foundation & Data Modeling

### Pydantic Schemas (`src/foundation_sar.py`)

| Schema                     | Purpose                 | Key Fields                                               |
|----------------------------|-------------------------|---------------------------------------------------------|
| `CustomerData`            | Customer profile        | `customer_id`, `name`, `risk_rating`, `customer_since` |
| `AccountData`             | Account details         | `account_id`, `customer_id`, `balance`, `account_type` |
| `TransactionData`         | Transaction record      | `transaction_id`, `amount`, `transaction_date`, `transaction_type` |
| `CaseData`                | Unified case object     | Links customer + accounts + transactions with `case_id`|
| `RiskAnalystOutput`       | Risk assessment result  | `classification`, `confidence_score`, `risk_level`, `key_indicators` |
| `ComplianceOfficerOutput` | SAR narrative           | `narrative`, `regulatory_citations`, `completeness_check` |
[file:243]

Validation rules include:

- `risk_rating` constrained to `['Low', 'Medium', 'High']`  
- `confidence_score` bounded `0.0–1.0`  
- `risk_level` constrained to `['Low', 'Medium', 'High', 'Critical']`  
- `classification` constrained to `['Structuring', 'Sanctions', 'Fraud', 'MoneyLaundering', 'Other']`  
- Date fields parsed with `datetime` validators  
- Optional fields default to `None` or `[]` to handle missing CSV values[file:243]

### DataLoader & ExplainabilityLogger

- **`DataLoader`** — merges `customers.csv`, `accounts.csv`, and `transactions.csv` into unified `CaseData` objects via `create_case_from_data()`.[file:243]  
- **`ExplainabilityLogger`** — writes structured JSONL audit entries with timestamps, identifiers, agent decisions, and reasoning chains to `outputs/audit_logs/`.[file:243][file:233]

---

## 🔍 Risk Analyst Agent — Chain-of-Thought

**File:** `src/risk_analyst_agent.py`

`RiskAnalystAgent` uses a Chain-of-Thought system prompt that enforces step-by-step reasoning:[file:233]

```text
Step 1: Identify transaction patterns (velocity, amounts, timing)
Step 2: Check for threshold structuring indicators ($8,000–$9,999 band)
Step 3: Assess counterparty and geographic risk
Step 4: Evaluate against known typologies
Step 5: Assign classification and confidence score
```

**Supported classifications:**

| Classification     | Trigger Pattern                                      |
|--------------------|------------------------------------------------------|
| `Structuring`      | Repeated transactions just below the $10K CTR threshold |
| `Sanctions`        | Counterparty matches watchlist indicators           |
| `Fraud`            | Account takeover or identity anomalies              |
| `Money_Laundering` | Layering via high-velocity in/out wire transfers    |
| `Other`            | Suspicious activity not fitting the above patterns  |
[file:233]

The agent outputs a `RiskAnalystOutput` with `confidence_score`, `risk_level`, and `key_indicators`, and falls back to a structured default if JSON parsing fails.[file:233]

---

## ⚖️ Compliance Officer Agent — ReACT Framework

**File:** `src/compliance_officer_agent.py`

`ComplianceOfficerAgent` implements a ReACT loop:[file:233]

```text
REASON → Analyze the risk findings and determine regulatory obligations
ACT    → Draft the SAR narrative with required elements
REASON → Verify narrative completeness against a checklist
ACT    → Add regulatory citations and finalize for submission
```

Narratives must:

- Be ≤ 120 words  
- Cover who, what, when, where, and why  
- Use a professional regulatory tone  
- Include citations such as `31 CFR 1020.320` and relevant BSA references[file:233]

The agent returns a `ComplianceOfficerOutput` with `narrative`, `narrative_reasoning`, `regulatory_citations`, and a `completeness_check` flag.[file:233]

---

## 🔄 Two-Stage Workflow

**File:** `src/demo_integration_pipeline.py`

### Stage 1 — Risk Screening

```python
selected_customers, rest_of_cases = screen_high_risk_customers(
    customers_data, accounts_data, transactions_data
)
```

Screening criteria: `risk_rating` in `['Medium', 'High']` and (`total_amount > 100000` or `transaction_count > 50`).[file:236]

### Stage 2 — 4-Agent Escalation Pipeline

```python
res1 = run_agent_pipeline(high_risk_cases, orchestrator, is_high_risk=True)
```

```text
Triage → Risk Analyst → Structuring Expert → Compliance Officer
  ↓            ↓                ↓                    ↓
Filter      CoT Analysis    Pattern Check      ReACT Narrative
```

Cases flagged `HUMAN_REVIEW` pause for manual review before narrative generation and SAR filing.[file:236][file:238]

---

## 📄 SAR Document Structure

Each approved case generates a JSON file under `outputs/filed_sars/`:[file:236]

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

### AI vs Human Review Policy

- **AI-only SARs**  
  - `sar_metadata.review_status = "ai_only"`  
  - `audit_trail.human_reviewer = null`  
  - Used when the AI pipeline meets a high-confidence threshold and no human explicitly reviews the case.[file:236]

- **Human-approved SARs**  
  - `sar_metadata.review_status = "human_approved"`  
  - `audit_trail.human_reviewer = "compliance_officer"`  
  - Used when a human compliance officer approves the case before narrative generation and filing.[file:236]

This policy can be audited easily through both the command line and the dashboard.[file:236]

---

## 📊 Audit Trail & Efficiency Metrics

Every agent decision is written to `outputs/audit_logs/` as JSONL:[file:233][file:236]

```json
{
  "case_id": "...",
  "customer_name": "...",
  "decision": "PROCEED",
  "ai_classification": "Money_Laundering",
  "ai_confidence": 0.91,
  "compliance_narrative_exists": true,
  "timestamp": "..."
}
```

`analyze_workflow_efficiency()` prints a workflow summary including processing volume, approval/rejection rates, and cost savings versus a manual baseline.[file:236]

### Workflow KPIs and Cost Model

The pipeline computes a “Corporate SAR Workflow Dashboard” with:[file:236]

- Total cases processed, SARs filed, and cases filtered early  
- Average AI processing time vs a 30-minute manual baseline and percentage time saved  
- AI vs human-only cost model and overall cost savings / ROI  
- High-confidence case rate (≥ 0.80) and triage filter rate  

These KPIs feed the Streamlit **Workflow Economics** and **AI Decision Analytics** tabs via `calculate_kpis`, `aggregate_sar_history`, and `export_live_session`.[file:236]

---

## 📈 Live Dashboard (`app.py`)

Launch with:

```bash
streamlit run app.py
```

| Tab                      | Contents                                                                |
|--------------------------|-------------------------------------------------------------------------|
| 📊 Overview              | Filing volume timeline, classification mix, data quality notes          |
| 🏷️ Classification & Confidence | Distribution charts, risk level breakdown, confidence histograms |
| 💰 Workflow Economics    | Interactive what-if cost/ROI calculator                                |
| 🤖 AI Decision Analytics | Agent roster, override tracking, top flagged customers                 |
| 🔎 Case Explorer         | Search by customer/SAR ID, full narrative drill-down, CSV export       |
| 🟢 Latest Run            | Current batch summary, per-case decisions, transaction drill-down      |
[file:236]

Data sources under `outputs/live_dashboard/` include `sar_history.csv`, `sar_history_meta.json`, and `live_session.json`.[file:236]

---

## 🔍 Inspecting Outputs from the Command Line

- **List all filed SARs**:  
  ```bash
  ls outputs/filed_sars/*.json
  ```
- **Filter human-approved SARs** (requires `jq`):  
  ```bash
  jq -e '
    .sar_metadata.review_status == "human_approved" and
    .audit_trail.human_reviewer == "compliance_officer"
  ' outputs/filed_sars/*.json
  ```
- **Filter AI-only SARs**:  
  ```bash
  jq -e '
    .sar_metadata.review_status == "ai_only" and
    .audit_trail.human_reviewer == null
  ' outputs/filed_sars/*.json
  ```
[file:236]

---

## 🧪 Testing

The project includes 30 tests across three modules.[file:233]

```bash
# Run all tests
python -m pytest tests/ -v

# Run individual modules
python -m pytest tests/test_foundation.py -v
python -m pytest tests/test_risk_analyst.py -v
python -m pytest tests/test_compliance_officer.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

| Module                  | Tests | Coverage Focus                                     |
|-------------------------|-------|----------------------------------------------------|
| `test_foundation.py`    | 10    | Schema validation, CSV loading, case aggregation, audit logging |
| `test_risk_analyst.py`  | 10    | Agent initialization, case analysis, JSON parsing, error handling |
| `test_compliance_officer.py` | 10 | Narrative generation, word-limit enforcement, citations, parsing |
[file:233]

### Integration & End-to-End Tests

`03_workflow_integration.ipynb` and `demo_integration_pipeline.py` include:[file:233][file:236]

- Component readiness checks (foundation, agents, tests)  
- Integration tests via pytest for all core components  
- A complete system demonstration that processes multiple customers, generates SARs, writes audit logs, and computes efficiency metrics  

---

## 📦 Dependencies

```text
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

Install everything:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Built With

- Python — core language  
- Pydantic — data validation and settings management  
- OpenAI API — LLM integration  
- Pandas — data manipulation and analysis  
- Jupyter — interactive development environment  
- pytest — testing framework  
- python-dotenv — environment variable management  
- Streamlit — live dashboard  
- Plotly — interactive charts  
- Matplotlib — data visualization[file:243][file:236]

**Methodologies:** Chain-of-Thought prompting, ReACT (Reasoning + Acting), multi-agent architecture, human-in-the-loop review.[file:233][file:236]

---

## ⚠️ Note

This project uses synthetic financial data for demonstration purposes. It illustrates AI-assisted detection and reporting techniques and is not a substitute for a production-grade regulatory compliance system.[file:233]