class MockRiskAnalyst:
    def analyze_case(self, case_data):
        # Returns an object that mimics the RiskAnalyst response structure
        return type('MockResponse', (object,), {
            'classification': 'High Risk',
            'confidence_score': 0.95,
            'risk_level': 'Level 3',
            'reasoning': 'Automated analysis detected rapid movement of funds across multiple high-risk accounts.',
            'key_indicators': ['Structured Deposits', 'Rapid Outflow']
        })

from types import SimpleNamespace

class MockComplianceOfficer:
    def generate_compliance_narrative(self, case_data, risk_analysis):
        # SimpleNamespace creates an object where you can set attributes directly
        return SimpleNamespace(
            narrative="The subject's transaction pattern exhibits high-velocity movement consistent with smurfing.",
            regulatory_citations=['Bank Secrecy Act (BSA)', 'USA PATRIOT Act Section 314(a)']
        )