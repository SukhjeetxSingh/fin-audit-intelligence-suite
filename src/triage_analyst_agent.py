# src/triage_analyst_agent
import json
from src.base_agent import BaseAgent

class TriageAgent(BaseAgent):
    def __init__(self, client, logger, model="gpt-3.5-turbo", use_mock=False):
        super().__init__(client, logger, agent_key="TRIAGE_ANALYST", model=model)
        self.use_mock = use_mock

    def execute(self, transaction_data):
        if self.use_mock:
            return self._generate_fallback(transaction_data)

        print(f"[{self.__class__.__name__}] Executing real API call.")
        try:
            transactions = (
                transaction_data.get("transactions", [])
                if isinstance(transaction_data, dict)
                else []
            )
            amounts = [
                t.get("amount", 0) if isinstance(t, dict) else getattr(t, "amount", 0)
                for t in transactions
            ]
            total = sum(amounts)
            count = len(amounts)

            tx_lines = "\n".join(
                f"  - ${t.get('amount', 0) if isinstance(t, dict) else getattr(t, 'amount', 0):,.2f}"
                f" | {t.get('transaction_type', '') if isinstance(t, dict) else getattr(t, 'transaction_type', '')}"
                f" | {t.get('transaction_date', '') if isinstance(t, dict) else getattr(t, 'transaction_date', '')}"
                for t in transactions[:20]
            )

            user_content = (
                f"[TRANSACTION DOSSIER]\n"
                f"Total Transactions : {count}\n"
                f"Total Amount       : ${total:,.2f}\n"
                f"Risk Rating        : {transaction_data.get('risk_rating', 'Unknown') if isinstance(transaction_data, dict) else 'Unknown'}\n\n"
                f"Transaction Details:\n{tx_lines}\n\n"
                f"Analyze the above for suspicious activity patterns per your system instructions.\n"
                f"Return ONLY a valid JSON object matching the expected output schema."
            )

            response = self.call_llm(user_content)
            data = json.loads(response) if isinstance(response, str) else response

            return {
                "status":                "COMPLETE" if data.get("confidence_score", 0) >= 0.6 else "INCOMPLETE",
                "is_suspicious":         bool(data.get("is_suspicious", False)),
                "primary_risk_category": data.get("primary_risk_category", "none"),
                "confidence_score":      float(data.get("confidence_score", 0.0)),
                "triage_summary":        data.get("triage_summary", "Analyzed"),
                "thought_process":       data.get("thought_process", ""),
                "feedback_addressed":    data.get("feedback_addressed", True),
            }

        except Exception as e:
            print(f"DEBUG [TriageAgent] Error: {e}")
            return {
                "status":    "INCOMPLETE",
                "reasoning": f"Triage agent unavailable — flagged for manual review. Error: {e}"
            }

    def _generate_fallback(self, transaction_data):
        transactions = transaction_data.get("transactions", []) if isinstance(transaction_data, dict) else []
        amounts = [t.get("amount", 0) if isinstance(t, dict) else getattr(t, "amount", 0) for t in transactions]
        
        near_threshold = [a for a in amounts if 8000 <= a <= 9999]
        total = sum(amounts)
        count = len(amounts)

        if near_threshold:
            return {
                "status": "COMPLETE",
                "is_suspicious": True,
                "primary_risk_category": "structuring",
                "thought_process": f"Identified {len(near_threshold)} transactions in the $8,000-$9,999 band. Pattern consistent with CTR threshold avoidance under 31 CFR 1020.320.",
                "triage_summary": f"{len(near_threshold)} near-threshold deposits detected out of {count} total transactions totaling ${total:,.2f}.",
                "confidence_score": 0.91,
                "feedback_addressed": True
            }

        if total > 50000:
            return {
                "status": "COMPLETE",
                "is_suspicious": True,
                "primary_risk_category": "velocity_spike",
                "thought_process": f"High aggregate volume of ${total:,.2f} across {count} transactions. Velocity exceeds expected profile.",
                "triage_summary": f"Aggregate transaction volume of ${total:,.2f} flagged for layering review.",
                "confidence_score": 0.78,
                "feedback_addressed": True
            }

        return {
            "status": "INCOMPLETE",
            "is_suspicious": False,
            "primary_risk_category": "none",
            "thought_process": f"Reviewed {count} transactions totaling ${total:,.2f}. No red-flag indicators detected.",
            "triage_summary": "No immediate patterns detected. Insufficient signals for automated triage.",
            "confidence_score": 0.45,
            "feedback_addressed": False
        }