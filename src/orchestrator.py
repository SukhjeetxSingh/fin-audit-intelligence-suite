# src/orchestrator.py
import json
from src.triage_analyst_agent import TriageAgent
from src.risk_analyst_agent import RiskAnalystAgent
from src.structuring_expert import StructuringExpert
from src.compliance_officer_agent import ComplianceOfficerAgent
from src.mock.mock_client import InternalMockClient


class FraudOrchestrator:

    def __init__(self, logger, client=None, use_mock=True,
                 triage=None, risk_analyst=None, expert=None, officer=None):
        self.logger = logger
        self.use_mock = use_mock
        self.client = client if client is not None else InternalMockClient()
        
        # Propagating use_mock to all agents for consistent behavior
        self.triage = triage or TriageAgent(client, logger, use_mock=self.use_mock)
        self.expert = expert or StructuringExpert(client, logger, use_mock=self.use_mock)
        self.risk_analyst = risk_analyst or RiskAnalystAgent(self.client, self.logger, use_mock=self.use_mock)
        self.officer = officer or ComplianceOfficerAgent(self.client, self.logger, use_mock=self.use_mock)

        # Cascade: enforce use_mock on ALL agents, injected or created
        for agent in [self.triage, self.expert, self.risk_analyst, self.officer]:
            if agent is not None:
                agent.use_mock = self.use_mock
        print(f"DEBUG [Orchestrator]: Received client ID {id(client)}")
        print(f"DEBUG [Orchestrator]: Assigned self.client ID {id(self.client)}")

    def _get_real_client(self):
        from openai import OpenAI
        return OpenAI()

    def inject_agents(self, triage, expert, officer):
        self.triage  = triage
        self.expert  = expert
        self.officer = officer

    def run_investigation(self, dossier):
        stages = [("Triage", self.triage), ("Expert", self.expert), ("Compliance", self.officer)]
        current_data = dossier.copy()
        current_data["_customer_name"] = dossier.get("customer", {}).get("name", "the client")
        
        max_retriage, retriage_count, i = 2, 0, 0

        while i < len(stages):
            stage_name, agent = stages[i]
            # Safety check for uninitialized agents
            if not agent:
                i += 1; continue
                
            result = agent.execute(current_data)
            print(f"DEBUG [{stage_name}]: status={result.get('status')}")

            # Feedback Loop Logic
            if stage_name == "Expert" and result.get("status") == "INCOMPLETE":
                if result.get("reasoning") == "missing_info_from_triage" and retriage_count < max_retriage:
                    retriage_count += 1
                    current_data["expert_feedback"] = result.get("detailed_reasoning", "")
                    i = 0; continue # Restart pipeline
                return {"status": "HALTED", "stage": stage_name, "reason": result.get("reasoning")}

            # Standard Failure Logic
            if result.get("status") == "INCOMPLETE":
                # Escalation logic for high risk
                if stage_name == "Triage" and current_data.get("risk_rating") in ["High", "Critical"]:
                    i = 1; continue 
                return {"status": "HALTED", "stage": stage_name, "reason": result.get("reasoning")}

            current_data.update(result)
            i += 1

        return {"status": "SUCCESS", "final_output": current_data}