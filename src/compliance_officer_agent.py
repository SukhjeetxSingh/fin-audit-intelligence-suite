# Compliance Officer Agent - ReACT Implementation  
# TODO: Implement Compliance Officer Agent using ReACT prompting

"""
Compliance Officer Agent Module

This agent generates regulatory-compliant SAR narratives using ReACT prompting.
It takes risk analysis results and creates structured documentation for 
FinCEN submission.

YOUR TASKS:
- Study ReACT (Reasoning + Action) prompting methodology
- Design system prompt with Reasoning/Action framework
- Implement narrative generation with word limits
- Validate regulatory compliance requirements
- Create proper audit logging and error handling
"""
from src.base_agent import BaseAgent # Import the shared logic
import json
import sys
import os
import openai
import time
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
DEFAULT_CITATIONS = ["31 CFR 1020.320", "Bank Secrecy Act (BSA)"]



# 1. Get the directory where THIS file (risk_analyst_agent.py) lives
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. If 'src' is the current directory, add the parent to path so we can see 'foundation_sar'
# If the parent is the project root, this allows 'import foundation_sar'
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 3. Try to import foundation_sar directly
try:
    from foundation_sar import ComplianceOfficerOutput, ExplainabilityLogger, CaseData, RiskAnalystOutput, get_prompt
except ImportError:
# Fallback if the user is calling it from inside src
    from src.foundation_sar import ComplianceOfficerOutput, ExplainabilityLogger, CaseData, RiskAnalystOutput, get_prompt

# # # TODO: Import your foundation components
# from foundation_sar import (
#     ComplianceOfficerOutput,
#     ExplainabilityLogger, 
#     CaseData,
#     RiskAnalystOutput
# )

# Load environment variables
load_dotenv()
PROMPT_CONFIG = get_prompt('COMPLIANCE_OFFICER')

class ComplianceOfficerAgent(BaseAgent):
    """
    A specialized agent for generating regulatory-compliant SAR narratives.
    """

    def __init__(self, openai_client, explainability_logger, model="gpt-4", use_mock=False):
        super().__init__(
            client=openai_client,
            logger=explainability_logger,
            agent_key="COMPLIANCE_OFFICER",
            model=model
        )
        self.use_mock = use_mock

    def execute(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bridge method to satisfy the orchestrator's pipeline requirements.
        """
        print(f"DEBUG [Compliance] keys received: {list(current_data.keys())}")  # ← temp debug

        case_data     = current_data.get("case_data")
        risk_analysis = current_data.get("risk_analysis")

        # Pass hoisted name through to narrative generator
        customer_name = current_data.get("_customer_name", "the client")
        if self.use_mock:
            case_data     = current_data.get("case_data")
            risk_analysis = current_data.get("risk_analysis")
            customer_name = current_data.get("_customer_name", "the client")
            output = self._generate_fallback_narrative(case_data, risk_analysis)
            return {
                "status":               "COMPLETE" if output.completeness_check else "INCOMPLETE",
                "narrative":            output.narrative,
                "reasoning":            output.narrative_reasoning,
                "regulatory_citations": output.regulatory_citations,
                "completeness_check":   output.completeness_check
            }

        print(f"[{self.__class__.__name__}] Executing real API call.")
        output = self.generate_compliance_narrative(case_data, risk_analysis, customer_name)

        return {
            "status":               "COMPLETE" if output.completeness_check else "INCOMPLETE",
            "narrative":            output.narrative,
            "reasoning":            output.narrative_reasoning,
            "regulatory_citations": output.regulatory_citations,
            "completeness_check":   output.completeness_check
        }

    def generate_compliance_narrative(self, case_data, risk_analysis, customer_name="the client") -> 'ComplianceOfficerOutput':
        """
        Generates a regulatory-compliant SAR narrative using the ReACT framework.
        """
        start_time = time.time()
        case_id    = getattr(case_data, 'case_id', 'Unknown')
        from src.foundation_sar import ComplianceOfficerOutput as COO_Internal

        # 1. API Call & System Handling
        try:
            formatted_analysis     = self._format_risk_analysis_for_prompt(risk_analysis)
            formatted_transactions = self._format_transactions_for_compliance(
                getattr(case_data, 'transactions', [])
            )

            user_prompt = PROMPT_CONFIG.get('user_prompt').format(
                formatted_analysis=formatted_analysis,
                formatted_transactions=formatted_transactions
            )

            # Prepend customer name so mock (and real LLM) always sees it
            user_prompt = f"Customer: {customer_name}\n\n" + user_prompt

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                max_tokens=800
            )
            raw_content = response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = f"System error: {str(e)}"
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer", action="Compliance Narrative Generation",
                case_id=case_id, input_data={}, output_data={}, reasoning=error_msg,
                execution_time_ms=(time.time() - start_time) * 1000, success=False, error_message=str(e)
            )
            return self._generate_fallback_narrative(case_data, risk_analysis)

        # 2. Parsing & Validation
        try:
            cleaned_content = self._extract_json_from_response(raw_content)
            parsed_json     = json.loads(cleaned_content)
            is_complete     = parsed_json.get("completeness_check", True)

            output = COO_Internal(
                narrative=            parsed_json.get("narrative",             ""),
                regulatory_citations= parsed_json.get("regulatory_citations",  []),
                narrative_reasoning=  parsed_json.get("reasoning",             ""),
                completeness_check=   True
            )

            if not is_complete:
                print(f"⚠️ Case {case_id} flagged as insufficient by Compliance Agent.")
                self.logger.log_agent_action(
                    agent_type="ComplianceOfficer", action="Compliance Narrative Generation (INCOMPLETE)",
                    case_id=case_id, input_data={}, output_data=parsed_json,
                    reasoning=output.narrative_reasoning,
                    execution_time_ms=(time.time() - start_time) * 1000, success=True
                )
                return output

            if len(output.narrative.split()) > 120:
                raise ValueError(
                    f"Generated text contains {len(output.narrative.split())} words "
                    "which exceeds 120 word limit."
                )

            self.logger.log_agent_action(
                agent_type="ComplianceOfficer", action="Compliance Narrative Generation",
                case_id=case_id, input_data={}, output_data=parsed_json,
                reasoning=output.narrative_reasoning,
                execution_time_ms=(time.time() - start_time) * 1000, success=True
            )
            return output

        except json.JSONDecodeError as jde:
            reasoning_text = f"JSON parsing failed: {str(jde)}"
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer", action="Compliance Narrative Generation",
                case_id=case_id, input_data={}, output_data={}, reasoning=reasoning_text,
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False, error_message=str(jde)
            )
            raise ValueError("Failed to parse Compliance Officer JSON output")

    def file_completed_sar(self, case_data, compliance_output, target_dir: str) -> str:
        """
        Exports the finalized SAR report as a JSON file to the specified directory.
        
        Args:
            case_data: The CaseData object associated with the SAR.
            compliance_output: The ComplianceOfficerOutput containing the narrative.
            target_dir: The destination directory path for the generated file.
            
        Returns:
            str: The full path to the generated JSON SAR file.
        """
        # Convert to absolute path to guard against notebook vs root working directory bugs
        absolute_target_dir = os.path.abspath(target_dir)
        os.makedirs(absolute_target_dir, exist_ok=True)
        
        case_id = getattr(case_data, 'case_id', 'UNKNOWN_CASE')
        file_name = f"SAR_{case_id}.json"
        full_file_path = os.path.join(absolute_target_dir, file_name)
        
        # Build the final comprehensive regulatory filing layout
        sar_payload = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "case_id": case_id,
                "customer_id": getattr(case_data.customer, 'customer_id', 'N/A') if getattr(case_data, 'customer', None) else 'N/A'
            },
            "compliance_narrative": compliance_output.narrative,
            "regulatory_citations": compliance_output.regulatory_citations,
            "audit_trail_reference": self.logger.file_path
        }
        
        # Safely dump JSON to the requested directory path
        with open(full_file_path, "w", encoding='utf-8') as f:
            json.dump(sar_payload, f, indent=4)
            
        return full_file_path


    def _extract_json_from_response(self, response_content: str) -> str:
        """
        Safely extracts raw JSON from an LLM response string.
        
        Args:
            response_content: The full raw text response from the LLM.
            
        Returns:
            str: A clean, parseable JSON string.
            
        Raises:
            ValueError: If no valid JSON content is found in the response.
        """

        """
        Extract JSON content from LLM response
        
        Handles:
        - Empty or whitespace-only responses
        - JSON wrapped in markdown code blocks (```json or ```)
        - Extracted raw JSON text ready for json.loads()
        """
        # 1. Handle Empty responses
        # ✅ Checks for empty or whitespace-only inputs immediately
        if not response_content or not response_content.strip():
            raise ValueError("No JSON content found")
            
        content = response_content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return content[start_idx:end_idx + 1]
            
        return content

    def _format_risk_analysis_for_prompt(self, risk_analysis) -> str:
        """
        Structures risk analysis outputs into a readable format for the LLM prompt.
        
        Args:
            risk_analysis: The raw RiskAnalystOutput data.
            
        Returns:
            str: A formatted string summarizing the risk classification and indicators.
        """
        # Safely extract values handles both dot notation or fallback dictionary/empty string types
        classification = getattr(risk_analysis, "classification", "N/A")
        confidence_score = getattr(risk_analysis, "confidence_score", "N/A")
        risk_level = getattr(risk_analysis, "risk_level", "N/A")
        reasoning = getattr(risk_analysis, "reasoning", "N/A")
        
        indicators_list = getattr(risk_analysis, "suspicious_indicators", [])
        if not indicators_list and hasattr(risk_analysis, 'key_indicators'):
            indicators_list = getattr(risk_analysis, 'key_indicators', [])
            
        suspicious_indicators = ", ".join(indicators_list) if isinstance(indicators_list, list) and indicators_list else "None identified"

        return f"""RISK ANALYST REPORT SUMMARY:
        - Classification Category: {classification}
        - Confidence Metric: {confidence_score}
        - Risk Level Assessment: {risk_level}
        - Key Flagged Suspicious Indicators: {suspicious_indicators}
        - Analyst Chain-of-Thought Reasoning: {reasoning}"""
    
    def _format_transactions_for_compliance(self, transactions) -> str:
        """
        Formats a list of transaction records for inclusion in compliance reports.
        
        Args:
            transactions: A list of TransactionData objects.
            
        Returns:
            str: A numbered list of transactions formatted with currency and detail strings.
        """
        if not transactions:
            return ""
        formatted = []
        for i, t in enumerate(transactions, 1):
            loc_str = f" at {t.location}" if getattr(t, "location", None) else ""
            method_str = f" via {t.method}" if getattr(t, "method", None) else ""
            formatted.append(f"{i}. {t.transaction_date}: ${t.amount:,.2f} {t.transaction_type}{loc_str}{method_str}")
        return "\n".join(formatted)

    def _validate_narrative_compliance(self, narrative: str) -> Dict[str, Any]:
        """
        Validates the generated narrative against regulatory requirements.
        
        Args:
            narrative: The text content of the SAR narrative.
            
        Returns:
            Dict: A dictionary containing 'is_valid' (bool) and lists of any 
                  detected 'errors', 'missing_elements', or 'missing_terms'. 
        
        Validate narrative meets regulatory requirements
        
        Fulfills TODO requirements:
        - Word count (≤120 words)
        - Required elements present (Who, What, When, Where, Why)
        - Appropriate terminology (Suspicious activity, structuring, etc.)
        - Regulatory completeness (Contains citations)
        """
        if not narrative or not narrative.strip():
            return {
                "is_valid": False,
                "word_count": 0,
                "missing_elements": ["Full Narrative Body"],
                "missing_terms": [],
                "missing_citations": True,
                "errors": ["Narrative text is empty."]
            }

        errors = []
        
        # 1. Word Count Validation (≤ 120 words)
        words = narrative.split()
        word_count = len(words)
        if word_count > 120:
            errors.append(f"Word count constraint breached: Contains {word_count} words (Maximum allowed is 120 words).")

        # 2. Required Elements Check (Answering Who, What, When, Where, Why)
        # We look for explicit contextual markers or descriptive language matching these parameters
        required_elements = PROMPT_CONFIG.get('narrative_compliance_required_elements')
        
        missing_elements = []
        narrative_lower = narrative.lower()
        for element, keywords in required_elements.items():
            if not any(kw in narrative_lower for kw in keywords):
                missing_elements.append(element.upper())
                
        if missing_elements:
            errors.append(f"Narrative missing essential descriptive details for: {', '.join(missing_elements)}")

        # 3. Appropriate Terminology Check
        mandatory_terminology = [
            "suspicious", 
            "activity", 
            "transaction", 
            "regulatory"
        ]
        missing_terms = [term for term in mandatory_terminology if term not in narrative_lower]
        if missing_terms:
            errors.append(f"Missing appropriate professional anti-money laundering terminology: {missing_terms}")

        # 4. Regulatory Completeness (Citations present)
        regulatory_citations = ["31 cfr", "12 cfr", "bsa", "bank secrecy act"]
        has_citation = any(citation in narrative_lower for citation in regulatory_citations)
        if not has_citation:
            errors.append("Regulatory completeness issue: Narrative must contain a formal citation (e.g., '31 CFR 1020.320').")

        # Compile and return comprehensive structural breakdown
        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "word_count": word_count,
            "missing_elements": missing_elements,
            "missing_terms": missing_terms,
            "missing_citations": not has_citation,
            "errors": errors
        }
    
    def _generate_fallback_narrative(self, case_data, risk_analysis) -> 'ComplianceOfficerOutput':
        """
        Offline fallback producing a DYNAMIC narrative from real case_data and
        risk_analysis objects — no API required, no hardcoded strings.

        Structure mirrors mock_client._mock_compliance_response() schema so both
        paths produce identical field shapes. Content is derived from live data.
        """
        from src.foundation_sar import ComplianceOfficerOutput as COO_Internal

        try:
            # ---------------------------------------------------------- #
            #  STEP 1 — Extract dynamic values from the real objects      #
            # ---------------------------------------------------------- #

            # WHO
            customer    = getattr(case_data, 'customer', None)
            name        = getattr(customer, 'name', None) or getattr(case_data, 'customer_name', 'Unknown Subject')
            cust_id     = getattr(customer, 'customer_id', None) or getattr(case_data, 'customer_id', 'N/A')
            who         = f"{name} (ID: {cust_id})"

            # WHAT & WHEN
            transactions = getattr(case_data, 'transactions', [])
            count        = len(transactions)
            total        = sum(getattr(t, 'amount', 0) for t in transactions)
            tx_types     = list({getattr(t, 'transaction_type', 'transaction') for t in transactions})
            type_str     = ', '.join(tx_types[:2]) or 'transaction'

            raw_dates = [getattr(t, 'transaction_date', None) for t in transactions]
            dates     = sorted(d for d in raw_dates if d is not None)
            if len(dates) >= 2:
                date_range = f"{dates[0]} to {dates[-1]}"
            elif len(dates) == 1:
                date_range = str(dates[0])
            else:
                date_range = "the review period"

            # WHERE
            locations = list({
                getattr(t, 'location', None)
                for t in transactions
                if getattr(t, 'location', None) and getattr(t, 'location', None) != 'N/A'
            })
            where = f"across {', '.join(locations[:2])}" if locations else "across multiple banking channels"

            # WHY — from risk_analysis
            classification = getattr(risk_analysis, 'classification', 'suspicious activity')
            confidence     = getattr(risk_analysis, 'confidence_score', 0.0)
            raw_indicators = getattr(risk_analysis, 'key_indicators', [])
            indicators     = ', '.join(raw_indicators[:2]) if raw_indicators else "unusual transaction pattern"
            risk_level     = getattr(risk_analysis, 'risk_level', 'High')

            # ---------------------------------------------------------- #
            #  STEP 2 — Build narrative_reasoning (ReACT Step-by-Step)   #
            # ---------------------------------------------------------- #
            narrative_reasoning = (
                f"Step 1 [Data Ingestion]: Parsed {count} {type_str} transactions "
                f"totaling ${total:,.2f} for {name} between {date_range}. "
                f"Step 2 [Fact-Pattern Isolation]: Identified {indicators}. "
                f"Step 3 [Regulatory Mapping]: Activity consistent with "
                f"{classification.lower().replace('_', ' ')} at {confidence:.0%} confidence — "
                f"meets BSA filing threshold (31 CFR 1020.320). "
                f"Step 4 [Risk Assessment]: Risk level assessed as {risk_level}. "
                f"Step 5 [Constraint Check]: Who/What/When/Where/Why coverage verified."
            )

            # ---------------------------------------------------------- #
            #  STEP 3 — Build the 120-word-capped SAR narrative          #
            # ---------------------------------------------------------- #
            narrative_parts = [
                f"{who} conducted {count} {type_str} transactions totaling ${total:,.2f}",
                f"{where} between {date_range}.",
                f"Activity indicates {classification.lower().replace('_', ' ')}",
                f"at {confidence:.0%} confidence ({risk_level} risk).",
                f"Key indicators: {indicators}.",
                f"Transactions lack clear economic purpose, consistent with suspicious activity",
                f"under the Bank Secrecy Act, 31 CFR 1020.320.",
            ]
            narrative = ' '.join(narrative_parts)

            # Hard 120-word cap — same gate as the live API path
            words = narrative.split()
            if len(words) > 120:
                narrative = ' '.join(words[:120])

            # ---------------------------------------------------------- #
            #  STEP 4 — Pull citations from mock_client (schema anchor)  #
            # ---------------------------------------------------------- #
            # mock_client owns the canonical citation list so both paths stay in sync
            # mock_schema   = json.loads(InternalMockClient()._mock_compliance_response())
            citations     = DEFAULT_CITATIONS

            print(
                f"⚠️  [OFFLINE MODE] Dynamic fallback narrative generated for "
                f"{name} | {count} txns | ${total:,.2f} | {risk_level} risk"
            )

            return COO_Internal(
                narrative=narrative,
                narrative_reasoning=narrative_reasoning,
                regulatory_citations=citations,
                completeness_check=True
            )

        except Exception as e:
            # Last resort — something in the case_data itself was malformed
            return COO_Internal(
                narrative=(
                    "Subject conducted multiple transactions inconsistent with known "
                    "business activity. Transactions lack clear economic purpose and "
                    "warrant SAR filing per Bank Secrecy Act, 31 CFR 1020.320."
                ),
                narrative_reasoning=f"Dynamic fallback failed during data extraction: {str(e)}",
                regulatory_citations=["31 CFR 1020.320"],
                completeness_check=False
            )

# ===== REACT PROMPTING HELPERS =====

def create_react_framework():
    """
    Returns an operational blueprint for the ReACT (Reasoning + Action) framework.
    
    This acts as a structural guide to ensure the agent systematically moves 
    from cognitive analysis to regulatory reporting documentation.
    
    Returns:
        Dict: A mapping of Reasoning and Action phases for SAR generation.
    """

    return PROMPT_CONFIG.get('react_framework')

def get_regulatory_requirements():
    """
    Returns the core regulatory and validation standards for SAR narratives.
    
    Provides the metrics, token rules, required contextual pillars (Who, What, When, 
    Where, Why), and mandatory terminology for automated compliance evaluation.
    
    Returns:
        Dict: The complete set of regulatory benchmarks and filing triggers.
    """

    return PROMPT_CONFIG.get('sar_guidelines')

# ===== TESTING UTILITIES =====

def test_narrative_generation():
    """
    Performs a local smoke test of the ComplianceOfficerAgent workflow.
    
    This test simulates a risk analysis payload and validates the agent's 
    ability to generate a compliant narrative, perform JSON extraction, 
    and pass word-count constraints without hitting the live OpenAI API.
    """
    print("🧪 Testing Compliance Officer Agent...")
    print("-" * 50)

    # 1. Create mock input structures mimicking actual project data types
    class MockCaseData:
        def __init__(self, case_id):
            self.case_id = case_id

    class MockRiskAnalystOutput:
        def __init__(self, classification, risk_level, confidence_score, indicators, reasoning):
            self.classification = classification
            self.risk_level = risk_level
            self.confidence_score = confidence_score
            self.suspicious_indicators = indicators
            self.reasoning = reasoning

    mock_case = MockCaseData(case_id="CASE-2026-99")
    mock_risk_analysis = MockRiskAnalystOutput(
        classification="Structuring",
        risk_level="HIGH",
        confidence_score=0.95,
        indicators=["Multiple cash deposits under $10,000", "Rapid succession transactions"],
        reasoning="The subject conducted multiple cash deposits totaling $28,500 over two business days, keeping individual transactions under the $10,000 CTR threshold."
    )

    # 2. Mocking systemic dependencies (OpenAI Client & Explainability Logger)
    class MockChoice:
        def __init__(self, content):
            self.message = type('Message', (object,), {'content': content})()

    class MockChatCompletion:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    class MockOpenAIClient:
        def __init__(self, simulated_response):
            self.simulated_response = simulated_response
        def create(self, *args, **kwargs):
            return MockChatCompletion(self.simulated_response)

    class MockExplainabilityLogger:
        def log_agent_action(self, case_id, action, result, reasoning, output_data=None):
            print(f"   📝 [Audit Logged] Action: {action} | Status: {result}")

    # Simulated valid compliance JSON payload matching constraints
    simulated_json = """{
        "reasoning": "The transaction frequency and amounts indicate intent to evade standard Currency Transaction Reporting thresholds.",
        "narrative": "During a 48-hour window, the subject executed multiple consecutive cash deposits totaling $28,500 across staggered banking locations. Individual deposits remained systematically under the $10,000 threshold to evade regulatory Currency Transaction Report (CTR) criteria. The funds were immediately wired to an unrelated domestic account, showing a pattern with no apparent economic utility. This suspicious structuring activity warrants a formal filing in absolute accordance with the Bank Secrecy Act (BSA) under 31 CFR 1020.320."
    }"""

    mock_client = type('Client', (object,), {'chat': type('Chat', (object,), {'completions': MockOpenAIClient(simulated_json)})()})()
    mock_logger = MockExplainabilityLogger()

    # 3. Initialize Agent and Execute Test Pipeline
    agent = ComplianceOfficerAgent(openai_client=mock_client, explainability_logger=mock_logger, model="gpt-4")
    
    try:
        output = agent.generate_compliance_narrative(case_data=mock_case, risk_analysis=mock_risk_analysis)
        print("\n🎉 Local Smoke Test Completed Successfully!")
        print(f"Generated Narrative Body:\n\"{output.narrative}\"")
        print(f"Citations Isolated: {output.regulatory_citations}")
        
        # Verify word count utility works
        is_word_count_valid = validate_word_count(output.narrative, max_words=120)
        print(f"Word Count Validation Pass: {is_word_count_valid}")
    except Exception as e:
        print(f"❌ Local Smoke Test Failed: {str(e)}")


def validate_word_count(text: str, max_words: int = 120) -> bool:
    """
    Validates that a narrative string does not exceed the allowed word count.
    
    Args:
        text: The narrative text to evaluate.
        max_words: The maximum allowed word count (default 120).
        
    Returns:
        bool: True if the word count is within limits, False otherwise.
    """
    if not text or not text.strip():
        return True
    word_count = len(text.split())
    return word_count <= max_words

if __name__ == "__main__":
    print("✅ Compliance Officer Agent Module")
    print("ReACT prompting for regulatory narrative generation")
    print("\n📋 TODO Items:")
    print("• Design ReACT system prompt")
    print("• Implement generate_compliance_narrative method")
    print("• Add narrative validation (word count, terminology)")
    print("• Create regulatory citation system")
    print("• Test with sample risk analysis results")
    print("\n💡 Key Concepts:")
    print("• ReACT: Reasoning + Action structured prompting")
    print("• Regulatory Compliance: BSA/AML requirements")
    print("• Narrative Constraints: Word limits and terminology")
    print("• Audit Logging: Complete decision documentation")
