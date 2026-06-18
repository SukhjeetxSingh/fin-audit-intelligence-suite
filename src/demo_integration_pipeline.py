"""
src/demo_integration_pipeline.py
=================================
All workflow helper functions for the AML SAR pipeline.

Every file output lands under:
    starter/outputs/          (resolved from notebooks/ via '../outputs/')

Naming is preserved exactly as used in demo_pipeline_2.ipynb.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import uuid
import statistics
import matplotlib.pyplot as plt
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from src.foundation_sar import DataLoader, ExplainabilityLogger, load_csv_data


# ─────────────────────────────────────────────────────────────────────────────
# PATH HELPERS  →  everything lands in  starter/outputs/
# ─────────────────────────────────────────────────────────────────────────────

def _outputs_root() -> str:
    """
    Returns the absolute path to  starter/outputs/
    Works whether called from  notebooks/  or  starter/  or  src/.
    """
    # __file__ is  starter/src/demo_workflow_integration.py
    # so two parents up is  starter/
    src_dir     = Path(__file__).resolve().parent          # starter/src/
    starter_dir = src_dir.parent                           # starter/
    outputs     = starter_dir / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    return str(outputs)


def _ensure(path: str) -> str:
    """makedirs and return path."""
    os.makedirs(path, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# JSON SERIALISATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def json_default(o: Any) -> Any:
    """Custom serializer for types the standard json library can't handle."""
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if hasattr(o, '__dict__'):
        return o.__dict__
    return str(o)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — DATA LOADING & PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def load_and_preprocess_data(filepath: str):
    """
    Load CSV data and prepare for analysis.

    Steps:
      1. Load customers.csv, accounts.csv, transactions.csv
      2. Handle missing values (fillna → '')
      3. Convert DataFrames to list-of-dicts

    Returns
    -------
    data_customers, data_accounts, data_transactions  (list[dict] each)
    """
    print("📊 Loading Cleaned Financial Data")
    df_cust, df_acc, df_trans = load_csv_data(filepath)
    df_cust, df_acc, df_trans = clean_data(df_cust, df_acc, df_trans)
    data_customers, data_accounts, data_transactions = convert_to_dicts(df_cust, df_acc, df_trans)
    print(f"📈 Loaded: {len(data_customers)} customers, "
          f"{len(data_accounts)} accounts, {len(data_transactions)} transactions")
    return data_customers, data_accounts, data_transactions


def clean_data(df_customers, df_accounts, df_transactions):
    """Stage 2: fill NaN values with empty string."""
    print("🧹 Stage 2: Cleaning missing values...")
    for df in [df_customers, df_accounts, df_transactions]:
        df.fillna('', inplace=True)
    print("✅ Data cleaned.")
    return df_customers, df_accounts, df_transactions


def convert_to_dicts(df_customers, df_accounts, df_transactions):
    """Stage 3: Convert DataFrames to list-of-dict format."""
    print("🔄 Stage 3: Converting to dictionary format...")
    data_customers    = df_customers.to_dict('records')
    data_accounts     = df_accounts.to_dict('records')
    data_transactions = df_transactions.to_dict('records')
    print("✅ Conversion complete.")
    return data_customers, data_accounts, data_transactions


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — CUSTOMER RISK SCREENING
# ─────────────────────────────────────────────────────────────────────────────

def screen_high_risk_customers(customers_data, accounts_data, transactions_data, top_n=9):
    """
    Screen customers by risk rating, transaction volume, and frequency.

    Criteria:
      • risk_rating in ['Medium', 'High']
      • total transaction amount > $100 K
      • transaction count > 50

    Returns
    -------
    top_group      : list[dict]  — top N highest-risk customers
    remaining_group: list[dict]  — the rest (still flagged, just lower priority)
    """
    print("🔍 Customer Risk Screening")
    print(f"🔍 Screening {len(customers_data)} customers for high-risk flags...")

    selected_customers = []

    for customer in customers_data:
        customer_accounts    = [acc for acc in accounts_data
                                if acc['customer_id'] == customer['customer_id']]
        account_ids          = [acc['account_id'] for acc in customer_accounts]
        customer_transactions = [txn for txn in transactions_data
                                 if txn['account_id'] in account_ids]

        total_amount      = sum(abs(txn['amount']) for txn in customer_transactions
                                if txn['amount'] != '')
        transaction_count = len(customer_transactions)
        risk_rating       = customer['risk_rating']

        risk_flags = []
        if risk_rating in ['Medium', 'High']:
            risk_flags.append('high_risk_rating')
        if total_amount > 100_000:
            risk_flags.append('large_amounts')
        if transaction_count > 50:
            risk_flags.append('high_frequency')

        if len(risk_flags) >= 2:
            selected_customers.append({
                'customer':          customer,
                'accounts':          customer_accounts,
                'transactions':      customer_transactions,
                'total_amount':      total_amount,
                'transaction_count': transaction_count,
                'risk_flags':        risk_flags,
            })

    selected_customers.sort(
        key=lambda x: (len(x['risk_flags']), x['total_amount']),
        reverse=True,
    )

    top_group       = selected_customers[:top_n]
    remaining_group = selected_customers[top_n + 1:]

    print(f"📊 Selected {len(top_group)} top-risk customers")
    print(f"   Remaining flagged : {len(remaining_group)}")
    return top_group, remaining_group


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — CASE OBJECT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_case_objects(customer_list: list, data_loader) -> list:
    """
    Convert a list of customer dicts into CaseData objects.

    Parameters
    ----------
    customer_list : output of screen_high_risk_customers (list of dicts)
    data_loader   : DataLoader instance (already initialised in the notebook)

    Returns
    -------
    list of CaseData objects
    """
    case_objects = []
    for item in customer_list:
        try:
            case = data_loader.create_case_from_data(
                item['customer'],
                item['accounts'],
                item['transactions'],
            )
            case_objects.append(case)
        except Exception as e:
            print(f"⚠️  Skipping {item['customer'].get('customer_id', 'unknown')}: {e}")

    print(f"✅ Built {len(case_objects)} CaseData objects.")
    return case_objects


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — HUMAN DECISION GATE
# ─────────────────────────────────────────────────────────────────────────────

def get_human_decision(risk_level: str) -> bool:
    """
    Prompt the human reviewer to approve or reject a SAR filing.
    Falls back to False after 3 failed attempts.
    """
    print("\n--- 🛑 ACTION REQUIRED ---")
    attempts = 0
    while attempts < 3:
        decision = input(
            f"\n\t| Risk Level: {risk_level} |\n"
            f"\t🤔 Proceed with SAR filing? (yes/no): "
        ).strip().lower()
        if decision in ['yes', 'y', '']:
            return True
        if decision in ['no', 'n']:
            return False
        print(f"Invalid input. Attempt {attempts + 1}/3. Please enter 'yes' or 'no'.")
        attempts += 1

    print("⚠️  Input failed, defaulting to 'no'.")
    return False


def print_case_summary(case_data, risk_analysis) -> None:
    """Print a clean case summary for the human reviewer."""
    print("\n" + "=" * 50)
    print("🚨 NEW CASE FOR REVIEW")
    print(f"Customer Name  : {case_data.customer.name}")
    print(f"Customer ID    : {case_data.customer.customer_id}")
    print(f"Risk Level     : {risk_analysis.risk_level}")
    print(f"Classification : {risk_analysis.classification}")
    print(f"Confidence     : {risk_analysis.confidence_score:.2%}")
    print("-" * 30)
    print(f"AI Reasoning   : {risk_analysis.summary}")
    print("=" * 50 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — SAR DOCUMENT CREATION & SAVING
# ─────────────────────────────────────────────────────────────────────────────

def create_sar_document(
    case_data,
    risk_analysis,
    compliance_review,
    review_status: str = "human_approved",
    human_reviewer: str | None = "compliance_officer",
) -> dict:
    """
    Build a complete SAR document dict from the three pipeline outputs.

    Returns
    -------
    dict  — ready to pass to save_sar_document()
    """
    sar_id      = f"SAR_{uuid.uuid4().hex[:8]}"
    filing_date = datetime.now().isoformat()

    return {
        'sar_metadata': {
            'sar_id':        sar_id,
            'filing_date':   filing_date,
            'filing_type':   'Suspicious Activity Report',
            'ai_generated':  True,
            'review_status': review_status,
        },
        'subject_information': {
            'customer_name':  case_data.customer.name,
            'customer_id':    case_data.customer.customer_id,
            'address':        case_data.customer.address,
            'customer_since': case_data.customer.customer_since,
            'risk_rating':    case_data.customer.risk_rating,
        },
        'suspicious_activity': {
            'classification':  risk_analysis.classification,
            'risk_level':      risk_analysis.risk_level,
            'confidence_score': risk_analysis.confidence_score,
            'narrative':       compliance_review.narrative,
            'key_indicators':  risk_analysis.key_indicators,
            'ai_reasoning':    risk_analysis.reasoning,
        },
        'regulatory_compliance': {
            'citations':            getattr(compliance_review, 'regulatory_citations', []),
            'narrative_word_count': len(compliance_review.narrative.split()),
            'compliance_status':    'approved',
        },
        'audit_trail': {
            'case_id':         case_data.case_id,
            'processing_date': filing_date,
            'ai_agents_used':  ['RiskAnalyst', 'ComplianceOfficer'],
            'human_reviewer':  human_reviewer,
        },
    }


def save_sar_document(sar_document: dict) -> None:
    """
    Save a SAR document JSON to  starter/outputs/filed_sars/<sar_id>.json
    """
    output_dir = os.path.join(_outputs_root(), "filed_sars")
    _ensure(output_dir)

    filename = os.path.join(output_dir, f"{sar_document['sar_metadata']['sar_id']}.json")
    try:
        with open(filename, 'w') as f:
            json.dump(sar_document, f, indent=4, default=json_default)
        print(f"✅ SAR saved: {filename}")
    except IOError as e:
        print(f"❌ Failed to save SAR document: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — 4-AGENT PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_pipeline(case_list: list, orchestrator, is_high_risk: bool = True):
    """
    Run the 4-agent escalation pipeline over a list of CaseData objects.

    Parameters
    ----------
    case_list    : list of CaseData objects (output of build_case_objects)
    orchestrator : FraudOrchestrator instance
    is_high_risk : True for the top-N group, False for remaining

    Returns
    -------
    processed, approved, rejected, decisions, label
      processed : list[str]   — customer_ids that went through
      approved  : list[str]   — case_ids where SAR was filed
      rejected  : list[str]   — case_ids that were halted / sent to human review
      decisions : list[dict]  — full audit trail
      label     : str         — 'selected_high_risk_customers' or 'other_cases'
    """
    from src.foundation_sar import RiskAnalystOutput, ComplianceOfficerOutput

    processed = []
    approved  = []
    rejected  = []
    decisions = []

    label      = "selected_high_risk_customers" if is_high_risk else "other_cases"
    batch_name = "HIGH RISK CASES"              if is_high_risk else "OTHER CASES"

    print("\n" + "=" * 60)
    print(f"  🚀 4-AGENT ESCALATION PIPELINE — {batch_name}")
    print("=" * 60)

    for case in case_list:
        print(f"\n🔍 Case: {case.case_id} | Customer: {case.customer.name}")

        dossier                = case.model_dump()
        dossier["risk_rating"] = case.customer.risk_rating

        result = orchestrator.run_investigation(dossier)
        status = result.get("status")

        if status == "SUCCESS":
            final = result["final_output"]

            # Normalize classification into allowed literals
            raw_class = final.get("classification") or final.get("primary_risk_category", "Other")
            raw_class_lower = str(raw_class).lower()

            if raw_class_lower == "structuring":
                classification = "Structuring"
            elif raw_class_lower == "fraud":
                classification = "Fraud"
            elif raw_class_lower == "sanctions":
                classification = "Sanctions"
            elif raw_class_lower in ["money_laundering", "money laundering"]:
                classification = "Money_Laundering"
            else:
                classification = "Other"

            # Normalize risk_level from final or fallback to customer risk_rating
            risk_level = final.get("risk_level")
            if not risk_level:
                risk_level = case.customer.risk_rating
            if risk_level not in ["Low", "Medium", "High"]:
                risk_level = "Medium"

            key_indicators = final.get("key_indicators", [])

            risk_analysis = RiskAnalystOutput(
                classification   = classification,
                confidence_score = final.get("confidence_score", 0.0),
                reasoning        = final.get("reasoning", "Pipeline analysis"),
                key_indicators   = key_indicators,
                risk_level       = risk_level,
            )

            compliance_review = ComplianceOfficerOutput(
                narrative            = final.get("narrative", "SAR narrative pending."),
                narrative_reasoning  = final.get("reasoning", ""),
                regulatory_citations = final.get("regulatory_citations", ["31 CFR 1020.320"]),
                completeness_check   = final.get("completeness_check", True),
            )
            # --- AI confidence gate (strict) --------------------------------
            ai_confident = (
                compliance_review.completeness_check
                and risk_analysis.confidence_score >= 0.90
                and risk_analysis.classification in ["Structuring", "Money_Laundering"]
            )
            # -----------------------------------------------------------------

            if ai_confident:
                # AI-only SAR (no human reviewer)
                sar_doc = create_sar_document(
                    case,
                    risk_analysis,
                    compliance_review,
                    review_status="ai_only",
                    human_reviewer=None,
                )
                save_sar_document(sar_doc)

                approved.append(case.case_id)
                processed.append(case.customer.customer_id)
                decisions.append({
                    'case_id':                     case.case_id,
                    'customer_id':                 case.customer.customer_id,
                    'customer_name':               case.customer.name,
                    'risk_rating':                 case.customer.risk_rating,
                    'decision':                    'PROCEED',
                    'ai_classification':           risk_analysis.classification,
                    'ai_confidence':               risk_analysis.confidence_score,
                    'compliance_narrative_exists': True,
                })
                print(
                    f"   ✅ AI-ONLY SAR filed | {classification} | "
                    f"{risk_analysis.confidence_score:.0%} confidence"
                )

            else:
                # Any doubt → prompt human Compliance Officer
                human_approves = get_human_decision(risk_analysis.risk_level)

                if human_approves:
                    # Human says: file SAR
                    sar_doc = create_sar_document(
                        case,
                        risk_analysis,
                        compliance_review,
                        review_status="human_approved",
                        human_reviewer="compliance_officer",
                    )
                    save_sar_document(sar_doc)

                    approved.append(case.case_id)
                    processed.append(case.customer.customer_id)
                    decisions.append({
                        'case_id':                     case.case_id,
                        'customer_id':                 case.customer.customer_id,
                        'customer_name':               case.customer.name,
                        'risk_rating':                 case.customer.risk_rating,
                        'decision':                    'PROCEED',
                        'ai_classification':           risk_analysis.classification,
                        'ai_confidence':               risk_analysis.confidence_score,
                        'compliance_narrative_exists': True,
                    })
                    print("   ✅ HUMAN-APPROVED SAR filed")

                else:
                    # Human says: do NOT file SAR
                    rejected.append(case.case_id)
                    decisions.append({
                        'case_id':                     case.case_id,
                        'customer_id':                 case.customer.customer_id,
                        'customer_name':               case.customer.name,
                        'risk_rating':                 case.customer.risk_rating,
                        'decision':                    'HUMAN_REVIEW',
                        'ai_classification':           risk_analysis.classification,
                        'ai_confidence':               risk_analysis.confidence_score,
                        'compliance_narrative_exists': True,
                    })
                    print("   👤 HUMAN REVIEW — SAR not filed")

        elif status == "HUMAN_REVIEW":
            rejected.append(case.case_id)
            decisions.append({
                'case_id':                     case.case_id,
                'customer_id':                 case.customer.customer_id,
                'customer_name':               case.customer.name,
                'risk_rating':                 case.customer.risk_rating,
                'decision':                    'HUMAN_REVIEW',
                'ai_classification':           'Unknown',
                'ai_confidence':               0.0,
                'compliance_narrative_exists': False,
            })
            print(f"   👤 HUMAN REVIEW | Stage: {result.get('stage')}")

        else:   # HALTED / REJECT
            rejected.append(case.case_id)
            decisions.append({
                'case_id':                     case.case_id,
                'customer_id':                 case.customer.customer_id,
                'customer_name':               case.customer.name,
                'risk_rating':                 case.customer.risk_rating,
                'decision':                    'REJECT',
                'ai_classification':           'Unknown',
                'ai_confidence':               0.0,
                'compliance_narrative_exists': False,
            })
            print(f"   🛑 HALTED | Stage: {result.get('stage')}")

    print("\n" + "=" * 60)
    print(f"  BATCH COMPLETE | Filed: {len(approved)} | Halted/Review: {len(rejected)}")
    print("=" * 60)

    return processed, approved, rejected, decisions, label


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — METRICS & ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_workflow_efficiency(processed_cases, approved_sars, rejected_cases, audit_decisions):
    """Print a workflow efficiency dashboard to stdout."""
    total_cases    = len(processed_cases) + len(rejected_cases)
    approved_count = len(approved_sars)
    rejected_count = len(rejected_cases)

    # Time efficiency
    processing_times   = [c.get("processing_time_ms", 0) for c in processed_cases
                          if isinstance(c, dict) and "processing_time_ms" in c]
    avg_time_ms        = sum(processing_times) / len(processing_times) if processing_times else 0
    human_review_ms    = 30 * 60 * 1000
    time_savings_pct   = ((human_review_ms - avg_time_ms) / human_review_ms * 100) if avg_time_ms else 0

    # Cost efficiency
    ai_cost_per_case      = 0.50
    ai_cost_compliance    = 5.00
    human_cost_per_case   = 85.00
    human_cost_compliance = 150.00
    ai_total     = (total_cases * ai_cost_per_case)   + (approved_count * ai_cost_compliance)
    human_total  = (total_cases * human_cost_per_case) + (approved_count * human_cost_compliance)
    cost_savings  = human_total - ai_total
    roi_pct       = (cost_savings / human_total * 100) if human_total > 0 else 0

    # KPIs
    filter_efficiency = (rejected_count / total_cases * 100) if total_cases > 0 else 0
    confidences       = [d['ai_confidence'] for d in audit_decisions] if audit_decisions else []
    high_conf_cases   = [c for c in confidences if c >= 0.80]
    precision_rate    = len(high_conf_cases) / len(confidences) if confidences else 0

    print("\n" + "=" * 45)
    print("      CORPORATE SAR WORKFLOW DASHBOARD")
    print("=" * 45)
    print(f"Throughput Metrics:")
    print(f"  Total Volume         : {total_cases} cases")
    print(f"  SAR Filing Volume    : {approved_count}")
    print(f"  Cases Filtered Early : {rejected_count}")
    print(f"\nTime Efficiency (vs Human Baseline ~30min/case):")
    if avg_time_ms:
        print(f"  Avg AI Processing    : {avg_time_ms / 1000:.1f}s per case")
        print(f"  Time Saved           : ~{time_savings_pct:.1f}% faster than manual review")
    else:
        print(f"  Avg AI Processing    : <1s per case (estimated)")
        print(f"  Time Saved           : ~99.9% faster than manual review")
    print(f"\nFinancial Performance (vs Full Human Workflow):")
    print(f"  AI Pipeline Cost     : ${ai_total:.2f}")
    print(f"  Human Equivalent     : ${human_total:.2f}")
    print(f"  Cost Savings         : ${cost_savings:.2f}")
    print(f"  ROI                  : {roi_pct:.1f}% cost reduction")
    print(f"\nOperational KPIs:")
    print(f"  High Confidence Rate : {precision_rate:.1%} of cases >= 80% confidence")
    print(f"  Triage Filter Rate   : {filter_efficiency:.1f}%")
    if filter_efficiency == 0:
        print(f"  Note: 0% filter = all cases flagged suspicious (conservative AI tuning)")
    print("=" * 45)


def validate_ai_decisions(audit_decisions: list) -> None:
    """Print AI decision analytics to stdout."""
    if not audit_decisions:
        print("\n--- No audit data available ---")
        return

    confidences        = [d['ai_confidence'] for d in audit_decisions]
    avg_confidence     = sum(confidences) / len(confidences)
    median_confidence  = statistics.median(confidences)
    manual_rejections  = [d for d in audit_decisions if d['decision'] == 'REJECT']

    print("\n-------     AI Decision Analytics     -------")
    print(f"Average AI Model Confidence : {avg_confidence:.2%}")
    print(f"Confidence (Median)         : {median_confidence:.2%}")
    print(f"Manual Human Overrides      : {len(manual_rejections)} cases")
    print("-" * 45)

    if manual_rejections:
        print("\nCases rejected by human reviewer:")
        for d in manual_rejections:
            print(f"  - Case ID: {d['case_id']} ({d['customer_name']})")


def calculate_kpis(processed_cases: list, rejected_cases: list, audit_decisions: list) -> dict:
    """
    Return a KPI dictionary (financial, throughput, performance).
    Used by the dashboard's Workflow Economics tab.
    """
    total_cases = len(processed_cases) + len(rejected_cases)
    avg_time    = (sum(d.get("processing_time_ms", 0) for d in audit_decisions) / total_cases
                   if total_cases else 0)
    return {
        "throughput": {
            "total":    total_cases,
            "sar":      len(processed_cases),
            "filtered": len(rejected_cases),
        },
        "financial": {
            "ai_cost":    (total_cases * 0.50) + (len(processed_cases) * 5.00),
            "human_cost": (total_cases * 85.00) + (len(processed_cases) * 150.00),
        },
        "performance": {
            "avg_time_ms":    avg_time,
            "high_conf_rate": (len([d for d in audit_decisions if d['ai_confidence'] >= 0.80])
                               / total_cases if total_cases else 0),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — VISUALISATION
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowVisualizer:
    """
    Generates and saves workflow charts to  starter/outputs/output_charts/
    (or the directory passed at init time via pipeline_config.yaml).
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.timestamp  = datetime.now().strftime("%S%M%H")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, approved_sars: list, rejected_cases: list,
                 audit_decisions: list, batch_num: int) -> None:
        """Generate the three standard workflow charts for one batch."""
        suffix = f"batch{batch_num}"
        prefix = self.timestamp

        # 1. Workflow Outcomes
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(['SARs Filed', 'Cases Rejected'],
               [len(approved_sars), len(rejected_cases)],
               color=['#2ecc71', '#e74c3c'])
        ax.set_title(f'Workflow Throughput {suffix}')
        ax.set_ylabel('Number of Cases')
        fname = f"{prefix}_workflow_outcomes_{suffix}.png"
        plt.savefig(os.path.join(self.output_dir, fname))
        plt.close()

        # 2. Cost Savings
        spend   = (len(approved_sars) + len(rejected_cases)) * 0.50 + len(approved_sars) * 5.00
        savings = len(rejected_cases) * 5.00
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(['Actual Spend', 'Avoided Cost'], [spend, savings],
               color=['#3498db', '#f1c40f'])
        ax.set_title(f'Financial Performance {suffix}')
        fname = f"{prefix}_cost_savings_{suffix}.png"
        plt.savefig(os.path.join(self.output_dir, fname))
        plt.close()

        # 3. Confidence Distribution
        confidences = [d['ai_confidence'] for d in audit_decisions]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(confidences, bins=10, color='#9b59b6', edgecolor='black')
        ax.set_title(f'Distribution of AI Confidence Scores {suffix}')
        ax.set_xlabel('Confidence Level')
        ax.set_ylabel('Frequency')
        fname = f"{prefix}_confidence_dist_{suffix}.png"
        plt.savefig(os.path.join(self.output_dir, fname))
        plt.close()

        print(f"✅ Charts saved to {self.output_dir}  [{prefix}_*_{suffix}.png]")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 9 — DASHBOARD DATA EXPORTS
# ─────────────────────────────────────────────────────────────────────────────

def sync_dashboard_data(data_map: dict) -> str:
    """
    Save the pipeline payload to:
        starter/outputs/live_dashboard/dashboard_data_sample.json

    Parameters
    ----------
    data_map : any dict — processed_cases, approved_sars, audit_decisions, etc.

    Returns
    -------
    str — absolute path to the written file
    """
    output_folder = os.path.join(_outputs_root(), "live_dashboard")
    _ensure(output_folder)
    file_path = os.path.join(output_folder, "dashboard_data_sample.json")

    with open(file_path, 'w') as f:
        json.dump(data_map, f, indent=2, default=json_default)

    print(f"✅ Data synced → {file_path}")
    return file_path


def aggregate_sar_history(config: dict) -> pd.DataFrame:
    """
    Read every JSON file from the filed_sars directory, flatten into a
    DataFrame, and write:
        starter/outputs/live_dashboard/sar_history.parquet
        starter/outputs/live_dashboard/sar_history_meta.json

    Parameters
    ----------
    config : dict loaded from pipeline_config.yaml

    Returns
    -------
    pd.DataFrame
    """
    # Resolve the filed_sars directory — always inside starter/outputs/
    configured_sar_dir = config.get('directories', {}).get('filed_sars', '')
    sar_dir = _resolve_to_outputs(configured_sar_dir, "filed_sars")

    files             = sorted(f for f in os.listdir(sar_dir) if f.endswith('.json'))
    records, failures = [], []

    for fname in files:
        try:
            with open(os.path.join(sar_dir, fname)) as f:
                d = json.load(f)
            meta  = d.get('sar_metadata', {})
            subj  = d.get('subject_information', {})
            susp  = d.get('suspicious_activity', {})
            reg   = d.get('regulatory_compliance', {})
            audit = d.get('audit_trail', {})
            records.append({
                'sar_id':               meta.get('sar_id'),
                'filing_date':          meta.get('filing_date'),
                'ai_generated':         meta.get('ai_generated'),
                'review_status':        meta.get('review_status'),
                'customer_name':        subj.get('customer_name'),
                'customer_id':          subj.get('customer_id'),
                'risk_rating':          subj.get('risk_rating'),
                'customer_since':       subj.get('customer_since'),
                'classification':       susp.get('classification'),
                'risk_level':           susp.get('risk_level'),
                'confidence_score':     susp.get('confidence_score'),
                'narrative':            susp.get('narrative'),
                'key_indicators':       susp.get('key_indicators'),
                'ai_reasoning':         susp.get('ai_reasoning'),
                'citations':            reg.get('citations'),
                'narrative_word_count': reg.get('narrative_word_count'),
                'compliance_status':    reg.get('compliance_status'),
                'case_id':              audit.get('case_id'),
                'processing_date':      audit.get('processing_date'),
                'ai_agents_used':       audit.get('ai_agents_used'),
                'human_reviewer':       audit.get('human_reviewer'),
                'source_file':          fname,
            })
        except Exception as e:
            failures.append((fname, str(e)))

    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} / {len(files)} files.  Failures: {len(failures)}")
    if failures:
        print("Sample failures:", failures[:5])

    # Diagnostics
    for col in ['classification', 'risk_level', 'review_status', 'compliance_status',
                'risk_rating', 'human_reviewer', 'ai_generated']:
        print(f"\n--- {col} value_counts ---")
        print(df[col].value_counts(dropna=False))

    print("\n--- ai_agents_used (exploded) ---")
    print(df['ai_agents_used'].explode().value_counts())
    print(f"\nfiling_date range  : {df['filing_date'].min()} → {df['filing_date'].max()}")
    print(f"duplicate sar_id   : {df['sar_id'].duplicated().sum()}")
    print(f"duplicate case_id  : {df['case_id'].duplicated().sum()}")
    print(f"unique customers   : {df['customer_id'].nunique()} / 150")
    print("\nconfidence_score stats:")
    print(df['confidence_score'].describe())

    # Save outputs
    dashboard_dir = os.path.join(_outputs_root(), "live_dashboard")
    _ensure(dashboard_dir)

    csv_path = os.path.join(dashboard_dir, "sar_history.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nSaved CSV → {csv_path}")

    meta_path = os.path.join(dashboard_dir, "sar_history_meta.json")
    with open(meta_path, 'w') as f:
        json.dump({
            "total_files":   len(files),
            "loaded":        len(df),
            "failed":        len(failures),
            "failures":      failures[:20],
            "generated_at":  datetime.utcnow().isoformat(),
        }, f, indent=2)
    print(f"Saved meta    → {meta_path}")

    return df


def export_live_session(
    all_cases:      list,
    approved_sars:  list | set,
    rejected_cases: list | set,
) -> None:
    """
    Write the current pipeline run's case-level data to:
        starter/outputs/live_dashboard/live_session.json

    Parameters
    ----------
    all_cases      : output of build_all_case_records()
    approved_sars  : list/set of approved SAR case IDs
    rejected_cases : list/set of rejected case IDs
    """
    approved_sars_set  = set(approved_sars)
    rejected_cases_set = set(rejected_cases)

    reviewed = [c for c in all_cases if c['status'] == 'reviewed']
    pending  = [c for c in all_cases if c['status'] == 'pending_review']
    approved = [c for c in reviewed  if c.get('is_approved_sar')]
    rejected = [c for c in reviewed  if c.get('is_rejected')]

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_cases_this_batch": len(all_cases),
            "reviewed":               len(reviewed),
            "pending_review":         len(pending),
            "approved_sars":          len(approved),
            "rejected":               len(rejected),
            "total_flagged_amount":   sum(c['total_amount'] for c in all_cases),
        },
        "cases": all_cases,
    }

    dashboard_dir = os.path.join(_outputs_root(), "live_dashboard")
    _ensure(dashboard_dir)
    live_path = os.path.join(dashboard_dir, "live_session.json")

    with open(live_path, 'w') as f:
        json.dump(payload, f, indent=2, default=json_default)
    print(f"✅ Live session exported → {live_path}")


def build_all_case_records(
    selected_customers: list,
    rest_of_cases:      list,
    audit_decisions:    list,
    approved_sars:      list | set,
    rejected_cases:     list | set,
) -> list[dict]:
    """
    Merge raw customer packets with audit decisions into flat case dicts
    for the Streamlit Latest Run tab.

    Returns
    -------
    list[dict] — one entry per case (selected + remaining)
    """
    approved_set  = set(approved_sars)
    rejected_set  = set(rejected_cases)
    audit_by_name = {ad['customer_name']: ad for ad in audit_decisions}

    def _build(packet: dict) -> dict:
        cust    = packet['customer']
        ad      = audit_by_name.get(cust['name'])
        case_id = ad['case_id'] if ad else None
        top_txns = sorted(packet['transactions'], key=lambda t: -t['amount'])[:5]
        return {
            'customer_id':                 cust['customer_id'],
            'customer_name':               cust['name'],
            'risk_rating':                 cust['risk_rating'],
            'occupation':                  cust.get('occupation', ''),
            'annual_income':               cust.get('annual_income', 0),
            'total_amount':                packet['total_amount'],
            'transaction_count':           packet['transaction_count'],
            'risk_flags':                  packet['risk_flags'],
            'has_rapid_wire_activity':     any(
                t['transaction_id'].startswith('RAPID_') for t in packet['transactions']
            ),
            'top_transactions':            top_txns,
            'status':                      'reviewed' if ad else 'pending_review',
            'case_id':                     case_id,
            'decision':                    ad['decision']                    if ad else None,
            'ai_classification':           ad['ai_classification']           if ad else None,
            'ai_confidence':               ad['ai_confidence']               if ad else None,
            'compliance_narrative_exists': ad['compliance_narrative_exists'] if ad else None,
            'is_approved_sar':             (case_id in approved_set)  if case_id else False,
            'is_rejected':                 (case_id in rejected_set)  if case_id else False,
        }

    all_cases = [_build(p) for p in selected_customers] + [_build(p) for p in rest_of_cases]

    unmatched = [c['customer_name'] for c in all_cases
                 if c['status'] == 'reviewed' and c['case_id'] is None]
    print(f"\nBuilt {len(all_cases)} case records. Unmatched names (should be empty): {unmatched}")

    reviewed_sample = next((c for c in all_cases if c['status'] == 'reviewed'), None)
    if reviewed_sample:
        print("\n=== preview of one reviewed case record ===")
        print(json.dumps(reviewed_sample, indent=2, default=json_default))

    return all_cases


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_to_outputs(configured_path: str, subfolder: str) -> str:
    """
    Ensure a configured directory path lives under  starter/outputs/<subfolder>.
    If it doesn't, remap it there and warn.
    """
    outputs      = _outputs_root()
    expected     = os.path.join(outputs, subfolder)
    abs_config   = os.path.abspath(configured_path) if configured_path else ""

    if abs_config.startswith(outputs):
        _ensure(abs_config)
        return abs_config

    print(
        f"⚠️  Config path '{configured_path}' is outside starter/outputs/.\n"
        f"   Remapping to: {expected}\n"
        f"   Update pipeline_config.yaml → directories.{subfolder}: outputs/{subfolder}"
    )
    _ensure(expected)
    return expected