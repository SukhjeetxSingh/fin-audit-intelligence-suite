# src/mock/mock_agent_output.py
from types import SimpleNamespace

class MockRiskAnalyst:

    def analyze_case(self, case_data):
        """
        Returns an object that mimics the RiskAnalystOutput structure but with
        safer default values that match the schema enums.
        """
        # Simple heuristic example using number of transactions if available
        txns = getattr(case_data, "transactions", [])
        count = len(txns)
        total = sum(getattr(t, "amount", 0) for t in txns)

        # Basic dynamic classification: no heavy logic, just to drive demos
        if count >= 10 and total > 25_000:
            classification = "Structuring"
            risk_level = "High"
            confidence = 0.85
            indicators = ["High transaction volume", "Potential threshold avoidance"]
        else:
            classification = "Other"
            risk_level = "Medium"
            confidence = 0.6
            indicators = [f"Total transactions: {count}", f"Total amount: ${total:,.2f}"]

        reasoning = (
            f"Step 1: Data review – analyzed {count} transactions totaling ${total:,.2f}. "
            f"Step 2: Pattern recognition – heuristic classification as {classification}. "
            f"Step 3: Regulatory mapping – risk level set to {risk_level} at {confidence:.0%} confidence."
        )

        return type(
            "MockResponse",
            (object,),
            {
                "classification": classification,
                "confidence_score": confidence,
                "risk_level": risk_level,
                "reasoning": reasoning,
                "key_indicators": indicators,
            },
        )

class MockComplianceOfficer:

    def generate_compliance_narrative(self, case_data, risk_analysis):
        """
        Lightweight mock that mirrors ComplianceOfficerOutput structure,
        but uses simplified logic.
        """
        customer = getattr(case_data, "customer", None)
        name = getattr(customer, "name", None) or getattr(case_data, "customer_name", "Unknown Subject")
        cust_id = getattr(customer, "customer_id", None) or getattr(case_data, "customer_id", "N/A")

        txns = getattr(case_data, "transactions", [])
        count = len(txns)
        total = sum(getattr(t, "amount", 0) for t in txns)
        tx_types = list({getattr(t, "transaction_type", "transaction") for t in txns})
        type_str = ", ".join(tx_types[:2]) or "transaction"

        raw_dates = [getattr(t, "transaction_date", None) for t in txns]
        dates = sorted(d for d in raw_dates if d is not None)
        if len(dates) >= 2:
            date_range = f"{dates[0]} to {dates[-1]}"
        elif len(dates) == 1:
            date_range = str(dates[0])
        else:
            date_range = "the review period"

        classification = getattr(risk_analysis, "classification", "suspicious activity")
        confidence = getattr(risk_analysis, "confidence_score", 0.0)
        risk_level = getattr(risk_analysis, "risk_level", "Medium")

        narrative = (
            f"{name} (ID: {cust_id}) conducted {count} {type_str} transactions totaling ${total:,.2f} "
            f"between {date_range}. Activity indicates {classification.lower().replace('_', ' ')} "
            f"at {confidence:.0%} confidence ({risk_level} risk). "
            "Transactions lack clear economic purpose, consistent with suspicious activity "
            "under the Bank Secrecy Act, 31 CFR 1020.320."
        )

        return SimpleNamespace(
            narrative=narrative,
            regulatory_citations=["31 CFR 1020.320", "Bank Secrecy Act (BSA)"],
        )