# src/structuring_expert.py
import json
from src.base_agent import BaseAgent

class StructuringExpert(BaseAgent):
    def __init__(self, client, logger, model="gpt-4o", use_mock=False): # Add use_mock
        super().__init__(client, logger, agent_key="STRUCTURING_EXPERT", model=model)
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
            dates = [
                t.get("transaction_date", "") if isinstance(t, dict) else getattr(t, "transaction_date", "")
                for t in transactions
            ]
            total = sum(amounts)
            count = len(amounts)

            tx_lines = "\n".join(
                f"  - ${t.get('amount', 0) if isinstance(t, dict) else getattr(t, 'amount', 0):,.2f}"
                f" | {t.get('transaction_type', '') if isinstance(t, dict) else getattr(t, 'transaction_type', '')}"
                f" | {t.get('transaction_date', '') if isinstance(t, dict) else getattr(t, 'transaction_date', '')}"
                f" | ID: {t.get('transaction_id', '') if isinstance(t, dict) else getattr(t, 'transaction_id', '')}"
                for t in transactions[:20]
            )

            user_content = (
                f"[TRANSACTION DOSSIER FOR STRUCTURING ANALYSIS]\n"
                f"Total Transactions : {count}\n"
                f"Total Amount       : ${total:,.2f}\n"
                f"Risk Rating        : {transaction_data.get('risk_rating', 'Unknown') if isinstance(transaction_data, dict) else 'Unknown'}\n"
                f"Date Range         : {min(dates) if dates else 'Unknown'} to {max(dates) if dates else 'Unknown'}\n\n"
                f"Transaction Breakdown:\n{tx_lines}\n\n"
                f"Perform a 7-day rolling window analysis and identify structuring or layering patterns.\n"
                f"Return ONLY a valid JSON object matching the expected output schema."
            )

            response = self.call_llm(user_content)
            raw_data = json.loads(response) if isinstance(response, str) else response

        except (json.JSONDecodeError, TypeError) as e:
            print(f"DEBUG [StructuringExpert] Error: {e}")
            return {
                "status":    "INCOMPLETE",
                "reasoning": "missing_info_from_triage"
            }

        data = {
            "status":                   raw_data.get("status",                   "INCOMPLETE"),
            "reasoning":                raw_data.get("reasoning",                "No reasoning provided"),
            "detailed_reasoning":       raw_data.get("detailed_reasoning",       "No details provided"),
            "pattern_found":            raw_data.get("pattern_found",            False),
            "layering_indicators":      raw_data.get("layering_indicators",      []),
            "recommended_sar_priority": raw_data.get("recommended_sar_priority", "High"),
            "feedback_addressed":       raw_data.get("feedback_addressed",       False),
        }

        reasoning     = data.get("reasoning", "").lower()
        is_vague      = "vague" in reasoning or len(reasoning) < 20
        pattern_found = data.get("pattern_found", False)

        data["status"] = "INCOMPLETE" if (is_vague or not pattern_found) else "COMPLETE"

        return data

    def _generate_fallback(self, transaction_data):
        transactions = transaction_data.get("transactions", []) if isinstance(transaction_data, dict) else []
        amounts = [t.get("amount", 0) if isinstance(t, dict) else getattr(t, "amount", 0) for t in transactions]

        near_threshold = [a for a in amounts if 8000 <= a <= 9999]
        total = sum(amounts)
        count = len(amounts)

        if near_threshold:
            return {
                "status": "COMPLETE",
                "analysis_depth": "detailed",
                "pattern_found": True,
                "layering_indicators": [
                    f"{len(near_threshold)} transactions in $8,000-$9,999 band",
                    f"Aggregate total ${total:,.2f} across {count} transactions",
                    "Possible smurfing — deliberate sub-threshold structuring detected"
                ],
                "reasoning": f"7-day rolling window analysis identified {len(near_threshold)} near-threshold transactions totaling ${total:,.2f}. Pattern consistent with structuring to evade CTR filing under 31 CFR 1020.320.",
                "recommended_sar_priority": "High"
            }

        if total > 50000:
            return {
                "status": "COMPLETE",
                "analysis_depth": "detailed",
                "pattern_found": True,
                "layering_indicators": [
                    f"High aggregate volume: ${total:,.2f}",
                    f"Transaction count: {count}",
                    "Velocity anomaly detected within review window"
                ],
                "reasoning": f"Rolling window aggregation flagged ${total:,.2f} across {count} transactions. Volume exceeds expected profile — possible layering activity.",
                "recommended_sar_priority": "Medium"
            }

        return {
            "status": "INCOMPLETE",
            "analysis_depth": "detailed",
            "pattern_found": False,
            "layering_indicators": [],
            "reasoning": f"Forensic audit of {count} transactions totaling ${total:,.2f} revealed no structuring bands, cool-down periods, or smurfing attempts. Additional data required.",
            "recommended_sar_priority": "Low"
        }