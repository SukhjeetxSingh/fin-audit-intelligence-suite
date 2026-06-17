# src/base_agent.py
import time
import json
from src.foundation_sar import get_prompt, get_model_strategy
from src.foundation_sar import ComplianceOfficerOutput


class BaseAgent:
    def __init__(self, client, logger, agent_key, model="gpt-4o"):
        self.client         = client
        self.logger         = logger
        self.model          = model
        self.config         = get_prompt(agent_key)
        self.system_prompt  = self.config.get('system_prompt')
        self.model_strategy = get_model_strategy()  # matches RiskAnalystAgent signature
        print(f"DEBUG [{self.__class__.__name__}]: Received client ID {id(client)}")

    def call_llm(self, user_content):
        """Standardized way to talk to OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

