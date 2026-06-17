# src/config_manager.py

# 1. Standard library and third-party imports at the TOP
import os
import yaml
import ipywidgets as widgets
from IPython.display import display

# Local imports (no src. prefix — matches your existing Vocareum path setup)
from foundation_sar import get_model_strategy
from risk_analyst_agent import RiskAnalystAgent
from compliance_officer_agent import ComplianceOfficerAgent
from triage_analyst_agent import TriageAgent
from structuring_expert import StructuringExpert


# ------------------------------------------------------------------ #
#  INTERNAL HELPERS — model config loading and ceiling resolution     #
# ------------------------------------------------------------------ #

def _load_model_config() -> dict:
    from foundation_sar import get_model_strategy
    return get_model_strategy()


def _resolve_model(agent_key: str, config: dict, ceiling_rank: int) -> str:
    """
    Returns the model for a given agent, capped to the user's ceiling tier.

    An agent's assigned model is used as-is when its tier rank <= ceiling rank.
    If the agent's assigned model exceeds the ceiling, it is downgraded to the
    ceiling tier's model instead.

    Example:
        COMPLIANCE_OFFICER wants gpt-4-turbo (rank 3)
        user ceiling is 'reasoning' (rank 2)
        → returns gpt-4o (rank 2) instead
    """
    agent_cfg   = config["agents"][agent_key]
    agent_tier  = agent_cfg["tier"]
    agent_rank  = config["tiers"][agent_tier]["rank"]

    if agent_rank <= ceiling_rank:
        return agent_cfg["model"]               # within ceiling — use assigned model
    else:
        ceiling_tier = next(
            v for v in config["tiers"].values() if v["rank"] == ceiling_rank
        )
        return ceiling_tier["model"]            # cap to ceiling model


# ------------------------------------------------------------------ #
#  PUBLIC API                                                         #
# ------------------------------------------------------------------ #

def initialize_agent_system(client, logger, user_choice: str = 'reasoning', use_mock: bool = False):
    """
    Instantiates all three agents with their fixed assigned models,
    capped to the user's selected tier ceiling.

    Agent → assigned model (from models.yaml):
        TRIAGE_ANALYST     → gpt-3.5-turbo   (always fast, never upgraded)
        STRUCTURING_EXPERT → gpt-4o           (mid tier)
        COMPLIANCE_OFFICER → gpt-4-turbo      (best reasoning)

    Ceiling effect of user_choice:
        'fast'      → all agents capped at gpt-3.5-turbo
        'reasoning' → Triage=gpt-3.5-turbo, Expert=gpt-4o, Compliance=gpt-4o (capped)
        'audit'     → all agents use their full assigned model, no cap applied

    Args:
        client (OpenAI | InternalMockClient):
            Authenticated API client. Pass InternalMockClient() for offline testing.
        logger (ExplainabilityLogger):
            Logger instance for recording agent decision steps and audit trails.
        user_choice (str, optional):
            Tier ceiling key — 'fast', 'reasoning', or 'audit'.
            Defaults to 'reasoning' (gpt-4o ceiling) when omitted entirely.

    Returns:
        tuple: (TriageAgent, StructuringExpert, ComplianceOfficerAgent, dict)
            - TriageAgent instance
            - StructuringExpert instance
            - ComplianceOfficerAgent instance
            - model_map dict: {'triage': str, 'expert': str, 'compliance': str}
    """
    from triage_agent import TriageAgent
    from base_agent import StructuringExpert
    from compliance_officer_agent import ComplianceOfficerAgent
    from risk_analyst_agent import RiskAnalystAgent

    config       = _load_model_config()
    FALLBACK     = 'reasoning'

    if user_choice not in config["tiers"]:
        print(f"⚠️  Unknown tier '{user_choice}' — falling back to '{FALLBACK}'")
        user_choice = FALLBACK

    ceiling_rank = config["tiers"][user_choice]["rank"]

    triage_model  = _resolve_model("TRIAGE_ANALYST",     config, ceiling_rank)
    analyst_model = _resolve_model("STRUCTURING_EXPERT", config, ceiling_rank)  # reuse mid-tier
    expert_model  = _resolve_model("STRUCTURING_EXPERT", config, ceiling_rank)
    compliance_model = _resolve_model("COMPLIANCE_OFFICER", config, ceiling_rank)

    triage     = TriageAgent(client, logger, model=triage_model, use_mock=use_mock)
    analyst    = RiskAnalystAgent(client, logger, model=analyst_model, use_mock=use_mock)
    expert     = StructuringExpert(client, logger, model=expert_model, use_mock=use_mock)
    compliance = ComplianceOfficerAgent(client, logger, model=compliance_model, use_mock=use_mock)

    model_map = {
        'triage':     triage_model,
        'analyst':    analyst_model,
        'expert':     expert_model,
        'compliance': compliance_model,
    }

    print(f"✅ Agent system initialized | ceiling='{user_choice}' (rank {ceiling_rank})")
    print(f"   TRIAGE_ANALYST     → {triage_model}")
    print(f"   RISK_ANALYST       → {analyst_model}")
    print(f"   STRUCTURING_EXPERT → {expert_model}")
    print(f"   COMPLIANCE_OFFICER → {compliance_model}")

    return triage, analyst, expert, compliance, model_map


def show_selection_details(key: str):
    """
    Prints a summary of what models will be assigned at the given tier ceiling.
    Used by the dropdown widget on_change handler.
    """
    config       = _load_model_config()
    tiers        = config.get("tiers", {})
    agents       = config.get("agents", {})

    if key not in tiers:
        print(f"⚠️  Unknown tier key: '{key}'")
        return

    ceiling_rank = tiers[key]["rank"]

    print(f"\n✅ Tier selected: '{key}' (ceiling rank {ceiling_rank})")
    print(f"{'Agent':<22} {'Assigned':<18} {'Effective (after ceiling)'}")
    print("-" * 62)

    for agent_key, agent_cfg in agents.items():
        assigned  = agent_cfg["model"]
        effective = _resolve_model(agent_key, config, ceiling_rank)
        capped    = " ← capped" if effective != assigned else ""
        print(f"  {agent_key:<20} {assigned:<18} {effective}{capped}")


# ------------------------------------------------------------------ #
#  WIDGET UI                                                          #
# ------------------------------------------------------------------ #

ui_output = widgets.Output()
_selector  = None


def get_model_input():
    """
    Renders an ipywidgets Dropdown for tier selection in a Jupyter notebook.
    Options are built from models.yaml tiers so the UI always stays in sync
    with the config — no hardcoded labels here.

    Returns:
        tuple: (_selector widget, ui_output Output widget)
    """
    global _selector
    config = _load_model_config()
    tiers  = config.get("tiers", {})

    # Sort tiers by rank so the dropdown reads fast → reasoning → audit
    sorted_tiers  = sorted(tiers.items(), key=lambda x: x[1]["rank"])
    model_choices = [
        (f"{k.capitalize()} — {v['model']}", k)
        for k, v in sorted_tiers
    ]

    if _selector is None:
        _selector = widgets.Dropdown(
            options=model_choices,
            value='reasoning',
            description='Model Tier:',
            style={'description_width': 'initial'}
        )

        def on_change(change):
            if change['name'] == 'value':
                ui_output.clear_output()
                with ui_output:
                    display(_selector)
                    show_selection_details(change['new'])

        _selector.observe(on_change, names='value')

    ui_output.clear_output()
    with ui_output:
        display(_selector)
        show_selection_details(_selector.value)  # show details for initial value on first render

    return _selector, ui_output