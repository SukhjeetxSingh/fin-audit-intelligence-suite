# src/mock/mock_client.py
import json
import re

class InternalMockClient:
    """Mock client for simulation and testing purposes."""
    def __init__(self):
        self.chat = self
        self.completions = self
        
    def create(self, **kwargs):
        messages = kwargs.get('messages', [])
        full_content = " ".join(str(m.get('content', '')) for m in messages)

        # --- Extract customer name ---
        # Try the hoisted _customer_name key first (most reliable)
        name_match = re.search(r"_customer_name['\"]:\s*['\"]([^'\"]+)", full_content)
        
        if name_match:
            customer_name = name_match.group(1).strip()
        else:
            # Fallback: try to parse the user message as a Python dict via ast
            import ast
            customer_name = "the client"
            for m in messages:
                content = m.get('content', '')
                if isinstance(content, str):
                    try:
                        data = ast.literal_eval(content)
                        name = (data.get('customer') or {}).get('name')
                        if name:
                            customer_name = name
                            break
                    except (ValueError, SyntaxError):
                        continue

        # --- Extract amount ---
        amount_match = re.search(r"\$([\d,]+)", full_content)
        txn_amt = amount_match.group(1) if amount_match else "28,500"

        system_prompt = messages[0]['content'] if messages else ""

        if "TRIAGE_ANALYST" in system_prompt:
            content = json.dumps({
                "status": "COMPLETE",
                "is_suspicious": True,
                "primary_risk_category": "structuring",
                "thought_process": f"Screening for {customer_name} shows deposits just below reporting thresholds.",
                "triage_summary": f"High risk identified for {customer_name}.",
                "confidence_score": 0.95,
                "feedback_addressed": True
            })
        else:
            long_reasoning = (
                f"Audit for {customer_name} reveals suspicious activity totaling ${txn_amt}. "
                f"The transaction pattern for {customer_name} is consistent with 'smurfing', "
                f"as identified by deposits structured just below the $10,000 threshold. "
                f"This activity, observed for {customer_name} across multiple branches, "
                "shows a clear intent to layer illicit proceeds and avoid reporting."
            )
            content = json.dumps({
                "status": "COMPLETE",
                "classification": "Structuring",
                "confidence_score": 0.85,
                "analysis_depth": "detailed",
                "pattern_found": True,
                "layering_indicators": ["threshold_avoidance_pattern", "rapid_account_cycling"],
                "reasoning": long_reasoning,
                "detailed_reasoning": long_reasoning,
                "recommended_sar_priority": "High",
                "feedback_addressed": True
            })

        return type('obj', (object,), {'choices': [
            type('obj', (object,), {'message': type('obj', (object,), {'content': content})()})
        ]})
    
    def get_compliance_schema_defaults(self) -> dict:
        """
        Returns the canonical field defaults for compliance output.
        Used by fallback generators so schema stays in sync with mock responses.
        """
        return {
            "regulatory_citations": ["31 CFR 1020.320", "Bank Secrecy Act (BSA)"],
            "completeness_check": True
        }