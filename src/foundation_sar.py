# file : project/starter/src/foundation_sar.py
# Foundation SAR - Core Data Schemas and Utilities
# TODO: Implement core Pydantic schemas and data processing utilities

"""
This module contains the foundational components for SAR processing:

1. Pydantic Data Schemas:
   - CustomerData: Customer profile information
   - AccountData: Account details and balances  
   - TransactionData: Individual transaction records
   - CaseData: Unified case combining all data sources
   - RiskAnalystOutput: Risk analysis results
   - ComplianceOfficerOutput: Compliance narrative results

2. Utility Classes:
   - ExplainabilityLogger: Audit trail logging
   - DataLoader: Combines fragmented data into case objects

YOUR TASKS:
- Study the data files in data/ folder
- Design Pydantic schemas that match the CSV structure
- Implement validation rules for financial data
- Create a DataLoader that builds unified case objects
- Add proper error handling and logging
"""

import json
import yaml
import math  # <----------
import pandas as pd
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
import uuid
import os
import logging  # <----------
from typing import Any # <----------

logger = logging.getLogger(__name__)  # <----------

from pydantic import BaseModel, ConfigDict, Field, field_validator

# CHANGED: Added shared helpers for NaN detection and date validation

def _is_nan_like(value: Any) -> bool:
    """Return True if value is a NaN-like sentinel (None, float('nan'), 'nan')."""
    if value is None:
        return True
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
    except TypeError:
        pass
    if str(value).strip().lower() == "nan":
        return True
    return False

def _validate_date_string(v: Any) -> str:
    """Coerce v to an ISO date string (YYYY-MM-DD) or raise ValueError."""
    if _is_nan_like(v):
        raise ValueError("Date value is missing or NaN.")
    s = str(v).strip()

    # CHANGED: Accept pandas Timestamp directly
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")

    # CHANGED: Try ISO then a few common formats
    try:
        parsed = datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        for fmt in ("%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Invalid date format '{s}'. Expected YYYY-MM-DD.")

    today = date.today()
    # CHANGED: Guard against impossible or future dates
    if parsed.year < 1900 or parsed.date() > today:
        raise ValueError(
            f"Date '{s}' is out of plausible range (1900–{today.isoformat()})."
        )
    return parsed.strftime("%Y-%m-%d")

# ===== TODO: IMPLEMENT PYDANTIC SCHEMAS =====

class CustomerData(BaseModel):
    """
    Schema for customer profile information.
    
    Validates customer demographic data, ensuring required fields are present
    and that the risk rating adheres to allowed enumeration values.
    """
    model_config = ConfigDict(from_attributes=True)

    customer_id: str = Field(..., description='Unique identifier like "CUST0001"')
    name: str = Field(..., min_length=1, description='Full customer name like "John Smith"')
    date_of_birth: str = Field(..., description='Date in YYYY-MM-DD format like "1985-03-15"')
    ssn_last_4: str = Field(..., description='Last 4 digits like "1234"')
    address: str = Field(..., min_length=1, description='Full address like "123 Main St, City, ST 12345"')
    customer_since: str = Field(..., description='Date in YYYY-MM-DD format like "2010-01-15"')
    risk_rating: Literal['Low', 'Medium', 'High'] = Field(..., description='Risk assessment')

    phone: Optional[str] = Field(None, description='Phone number like "555-123-4567"')
    occupation: Optional[str] = Field(None, description='Job title like "Software Engineer"')
    annual_income: Optional[float] = Field(
        None,
        ge=0,
        le=10_000_000,
        description='Yearly income like 75000'
    )

        # CHANGED: Coerce int/NaN ssn_last_4 from CSV to 4-digit string
    @field_validator("ssn_last_4", mode="before")
    @classmethod
    def coerce_ssn(cls, v: Any) -> str:
        if _is_nan_like(v):
            return ""
        s = str(v).strip()
        # Drop trailing .0 from pandas ints
        if "." in s:
            s = s.split(".")[0]
        if not s.isdigit():
            raise ValueError(f"Invalid ssn_last_4 '{s}' – must be digits.")
        return s.zfill(4)[:4]

    # CHANGED: Enforce valid date string for date_of_birth
    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> str:
        return _validate_date_string(v)

    # CHANGED: Enforce valid date string for customer_since
    @field_validator("customer_since", mode="before")
    @classmethod
    def validate_customer_since(cls, v: Any) -> str:
        return _validate_date_string(v)

    # CHANGED: Coerce annual_income and handle NaN as None
    @field_validator("annual_income", mode="before")
    @classmethod
    def coerce_annual_income(cls, v: Any) -> Optional[float]:
        if _is_nan_like(v):
            return None
        try:
            return float(str(v))
        except (TypeError, ValueError):
            return None

    # CHANGED: Normalise Optional string fields (NaN/blank → None)
    @field_validator("phone", "occupation", mode="before")
    @classmethod
    def coerce_optional_str(cls, v: Any) -> Optional[str]:
        if _is_nan_like(v):
            return None
        s = str(v).strip()
        return s or None

class AccountData(BaseModel):
    """
    Schema for financial account details.
    
    Ensures account records contain valid links to customers, appropriate 
    monetary formatting, and status definitions.
    """
    model_config = ConfigDict(from_attributes=True)
    # TODO: Implement the AccountData schema
    account_id: str = Field(..., description="Unique identifier")
    customer_id: str = Field(..., description="Must match CustomerData.customer_id")
    account_type: str = Field(..., description="Type like Checking, Savings, Money_Market")
    opening_date: str = Field(..., description="Date in YYYY-MM-DD format")
    current_balance: float = Field(..., description="Current balance (can be negative)")
    average_monthly_balance: float = Field(..., description="Average balance")
    status: str = Field(..., description="Status like Active, Closed")

    # CHANGED: Enforce valid opening_date
    @field_validator("opening_date", mode="before")
    @classmethod
    def validate_opening_date(cls, v: Any) -> str:
        return _validate_date_string(v)

    # CHANGED: Coerce balances and enforce plausible range
    @field_validator("current_balance", "average_monthly_balance", mode="before")
    @classmethod
    def coerce_balance(cls, v: Any) -> float:
        if _is_nan_like(v):
            raise ValueError("Balance value is missing or NaN.")
        try:
            val = float(str(v))
        except (TypeError, ValueError):
            raise ValueError(f"Balance '{v}' is not a valid number.")
        if not (-10_000_000 <= val <= 100_000_000):
            raise ValueError(
                f"Balance {val} is outside the allowed range [-10,000,000 … 100,000,000]."
            )
        return val

    # CHANGED: Ensure IDs are non-empty strings
    @field_validator("account_id", "customer_id", mode="before")
    @classmethod
    def coerce_id_str(cls, v: Any) -> str:
        if _is_nan_like(v):
            raise ValueError("ID field must not be missing.")
        return str(v).strip()

class TransactionData(BaseModel):
    """
    Schema for individual financial transaction records.
    
    Validates transaction amounts, methods, and linkages to specific 
    account IDs, supporting both debits and credits.
    """
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str = Field(..., description="Unique identifier")
    account_id: str = Field(..., description="Must match AccountData.account_id")
    transaction_date: str = Field(..., description="Date in YYYY-MM-DD format")
    transaction_type: str = Field(..., description="Type like Cash_Deposit")
    amount: float = Field(..., description="Transaction amount")
    description: str = Field(..., description="Transaction description")
    method: str = Field(..., description="Method like Wire, ACH")
    counterparty: Optional[str] = Field(None, description="Other party in transaction")
    location: Optional[str] = Field(None, description="Transaction location or branch")

        # CHANGED: Enforce valid transaction date
    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, v: Any) -> str:
        return _validate_date_string(v)

    # CHANGED: Enforce amount range and reject NaN
    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> float:
        if _is_nan_like(v):
            raise ValueError("Transaction amount is missing or NaN.")
        try:
            val = float(str(v))
        except (TypeError, ValueError):
            raise ValueError(f"Amount '{v}' is not a valid number.")
        if not (-1_000_000_000 <= val <= 1_000_000_000):
            raise ValueError(
                f"Amount {val} is outside the plausible range "
                "[-1,000,000,000 … 1,000,000,000]."
            )
        return val

    # CHANGED: Normalise optional text fields from NaN/blank → None
    @field_validator("counterparty", "location", mode="before")
    @classmethod
    def coerce_optional_fields(cls, v: Any) -> Optional[str]:
        if _is_nan_like(v):
            return None
        s = str(v).strip()
        return s or None

    # CHANGED: Ensure description/method are non-empty strings
    @field_validator("description", "method", mode="before")
    @classmethod
    def coerce_required_str(cls, v: Any) -> str:
        if _is_nan_like(v):
            return "N/A"
        return str(v).strip()

    # CHANGED: Ensure IDs are non-empty strings
    @field_validator("transaction_id", "account_id", mode="before")
    @classmethod
    def coerce_txn_id_str(cls, v: Any) -> str:
        if _is_nan_like(v):
            raise ValueError("ID field must not be missing.")
        return str(v).strip()


class CaseData(BaseModel):
    """
    Unified case object representing an entire financial crime investigation.
    
    Combines customer, account, and transaction data into a single, validated 
    investigative unit. Includes metadata and timestamping for auditability.
    
    Attributes:
        case_id: Unique identifier for the investigation.
        customer: CustomerData schema instance.
        accounts: List of associated AccountData schema instances.
        transactions: List of associated TransactionData schema instances.
    """
    model_config = ConfigDict(from_attributes=True)
    # TODO: Implement the CaseData schema with validation
    case_id: str
    customer: CustomerData
    accounts: List[AccountData]
    transactions: List[TransactionData]
    case_created_at: str
    data_sources: Dict[str, str]

    # CHANGED: Ensure each case has at least one transaction
    @field_validator('transactions')
    @classmethod
    def validate_transactions_not_empty(cls, v):
        if not v:
            raise ValueError("Transactions list cannot be empty.")
        return v

    # CHANGED: Ensure all accounts belong to the same customer
    @field_validator('accounts')
    @classmethod
    def validate_accounts_belong_to_customer(cls, v, info):
        if 'customer' not in info.data:
            return v
        customer_id = info.data.get('customer').customer_id
        for account in v:
            if account.customer_id != customer_id:
                raise ValueError(
                    f"Account {account.account_id} does not belong to customer {customer_id}"
                )
        return v


class RiskAnalystOutput(BaseModel):
    """
    Structured output schema for the Risk Analyst Agent's analysis.
    
    Captures the results of the Chain-of-Thought reasoning process, 
    enforcing classification types and risk-level constraints.
    """
    model_config = ConfigDict(from_attributes=True)
    # TODO: Implement the RiskAnalystOutput schema
    classification: Literal['Structuring', 'Sanctions', 'Fraud', 'Money_Laundering', 'Other']
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., max_length=500)
    key_indicators: List[str]
    risk_level: Literal['Low', 'Medium', 'High', 'Critical']
    

class ComplianceOfficerOutput(BaseModel):
    """
    Structured output schema for the Compliance Officer Agent's narrative.
    
    Enforces regulatory narrative constraints, including word limits, 
    required citations, and completeness flags.
    """
    model_config = ConfigDict(from_attributes=True)
    # TODO: Implement the ComplianceOfficerOutput schema
    narrative: str = Field(..., max_length=1000)
    narrative_reasoning: str = Field(..., max_length=500)
    regulatory_citations: List[str]
    completeness_check: bool
    

# ===== TODO: IMPLEMENT AUDIT LOGGING =====

class ExplainabilityLogger:
    """
    Manages the audit trail for all agent interactions within the system.
    
    This class ensures all decisions, reasoning steps, and agent outputs 
    are recorded in a structured JSONL format, providing a defensible 
    audit trail for regulatory examination.
    
    Attributes:
        file_path: Absolute path to the JSONL log file.
        entries: In-memory store of all logged actions.
    """
    model_config = ConfigDict(from_attributes=True)
    
    def __init__(self, file_path: str = "sar_audit.jsonl", verbose = False):
        """
        Initializes the logger and ensures the audit log directory exists.
        
        Args:
            file_path: Relative or absolute path to the audit log file.
        """


        # Resolve to an absolute path immediately so working directory shifts never break file writes
        # 1. Define your project's standard log location
        project_log_dir = os.path.join(os.getcwd(), "..", "outputs", "audit_logs")
        
        # 2. If the user passed the default filename, redirect it to the project folder
        if file_path == "sar_audit.jsonl":
            file_path = os.path.join(project_log_dir, file_path)
        
        # 3. Resolve to absolute path
        self.file_path = os.path.abspath(file_path)
        self.verbose = verbose
        
        # 4. Create directory if needed
        log_dir = os.path.dirname(self.file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        self.entries = []
    
    def log_agent_action(
        self, 
        agent_type: str, 
        action: str, 
        case_id: str, 
        input_data: Dict, 
        output_data: Dict, 
        reasoning: str, 
        execution_time_ms: float, 
        success: bool = True, 
        error_message: Optional[str] = None
        ) -> None:
        """
        Logs an agent operation to the JSONL audit trail.
        
        Args:
            agent_type: The source agent (e.g., 'DataLoader', 'RiskAnalyst').
            action: The specific action performed (e.g., 'analyze_case').
            case_id: The identifier for the case processed.
            input_data: Dictionary of input parameters.
            output_data: Dictionary of resulting data.
            reasoning: The agent's step-by-step reasoning or internal logs.
            execution_time_ms: Latency of the operation in milliseconds.
            success: Boolean status of the operation.
            error_message: Optional error details if success is False.
        """
        # TODO: Implement logging with structured entry creation and file writing
        """Log an agent action with essential context"""
        # 1. Create entry directly from the arguments
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'case_id': case_id,
            'agent_type': agent_type,
            'action': action,
            'input_summary': str(input_data),
            'output_summary': str(output_data),
            'reasoning': reasoning,
            'execution_time_ms': execution_time_ms,
            'success': success,
            'error_message': error_message
        }
        # 2. Store in memory list (Crucial for the pytest assertion)
        self.entries.append(log_entry)
        if self.verbose:
            print(f"DEBUG: Logging action '{action}' for case {case_id}")     

        # 3. Append to file
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
            

# ===== TODO: IMPLEMENT DATA LOADER =====

class DataLoader:
    """
    Transforms raw CSV-extracted dictionary data into validated CaseData objects.
    
    This class acts as the ingestion gatekeeper, handling data cleaning, 
    filtering, and schema assembly while providing performance logging.
    """
    model_config = ConfigDict(from_attributes=True)
    
    def __init__(self, explainability_logger: ExplainabilityLogger):
        """
        Initializes the loader with an audit logger.
        
        Args:
            explainability_logger: Logger for tracking case creation performance.
        """
        self.logger = explainability_logger
    
    def create_case_from_data(self, 
                            customer_data: Dict,
                            account_data: List[Dict],
                            transaction_data: List[Dict]) -> CaseData:
        """
        Assembles a unified CaseData object from fragmented data sources.
        
        Args:
            customer_data: Dictionary of customer profile fields.
            account_data: List of dictionaries for customer accounts.
            transaction_data: List of dictionaries for customer transactions.
            
        Returns:
            CaseData: The validated, unified case investigative unit.
            
        Raises:
            Exception: If validation fails or data relationships are inconsistent.
        """

        start_time = datetime.now()
        case_id = str(uuid.uuid4())

        # TODO: Implement complete case creation with error handling and logging
        try:
            # 1. Clean customer profile fields against Pandas NaN/type drift
            customer_clean = customer_data.copy()
            if 'ssn_last_4' in customer_clean and customer_clean['ssn_last_4'] is not None:
                customer_clean['ssn_last_4'] = str(customer_clean['ssn_last_4'])
                if str(customer_clean['ssn_last_4']).lower() == 'nan' or customer_clean['ssn_last_4'] != customer_clean['ssn_last_4']:
                    customer_clean['ssn_last_4'] = ""
                
            if 'customer_id' in customer_clean and customer_clean['customer_id'] is not None:
                customer_clean['customer_id'] = str(customer_clean['customer_id'])

            # Build CustomerData Schema
            customer = CustomerData(**customer_clean)
            
            # 2. Filter and build AccountData Schemas
            filtered_accounts = [
                AccountData(**acc) for acc in account_data 
                if str(acc.get('customer_id')) == customer.customer_id
            ]
            
            account_ids = {str(acc.account_id) for acc in filtered_accounts}
                
            # 3. Filter and clean TransactionData Schemas (Shielded from NaN drops)
            filtered_transactions = []
            for txn in transaction_data:
                if str(txn.get('account_id')) in account_ids:
                    txn_clean = txn.copy()
                    txn_clean['account_id'] = str(txn_clean['account_id'])
            
                    # 🧼 Clean Counterparty Column
                    cp = txn_clean.get('counterparty')
                    if cp is None or str(cp).lower() == 'nan' or cp != cp:
                        txn_clean['counterparty'] = "N/A"
                    else:
                        txn_clean['counterparty'] = str(cp)
                    
                    # 🧼 Clean Location Column (Defuses the current Pydantic crash)
                    loc = txn_clean.get('location')
                    if loc is None or str(loc).lower() == 'nan' or loc != loc:
                        txn_clean['location'] = "N/A"
                    else:
                        txn_clean['location'] = str(loc)
                
                    filtered_transactions.append(TransactionData(**txn_clean))
            
            # 4. Generate Metadata tracking (Safely out of the transaction loop scope)
            current_date_str = datetime.now().strftime('%Y%m%d')
            data_sources = {
                'customer_source': f"csv_extract_{current_date_str}",
                'account_source': f"csv_extract_{current_date_str}",
                'transaction_source': f"csv_extract_{current_date_str}"
            }
            case_created_at = datetime.now(timezone.utc).isoformat()
            
            # 5. Build Unified Case Payload
            unified_case = CaseData(
                case_id=case_id,
                customer=customer,
                accounts=filtered_accounts,
                transactions=filtered_transactions,
                case_created_at=case_created_at,
                data_sources=data_sources
            )
            
            # 6. Log success execution metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={"customer_id": customer.customer_id},
                output_data={
                    "case_id": case_id, 
                    "accounts_count": len(filtered_accounts), 
                    "transactions_count": len(filtered_transactions)
                },
                reasoning="Successfully bundled fragmented CSV dictionary items into unified CaseData object.",
                execution_time_ms=execution_time_ms,
                success=True
            )
            
            return unified_case

        except Exception as e:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={"customer_data": customer_data},
                output_data={},
                reasoning="Failed during CaseData pipeline assembly.",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )
            raise e
        

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """
    Loads raw CSV data files for processing.
    
    Args:
        data_dir: Directory containing the customer, account, and transaction CSVs.
        
    Returns:
        tuple: (customers_df, accounts_df, transactions_df) as Pandas DataFrames.
    """
    try:
        customers_df = pd.read_csv(f"{data_dir}/customers.csv")
        accounts_df = pd.read_csv(f"{data_dir}/accounts.csv") 
        transactions_df = pd.read_csv(f"{data_dir}/transactions.csv")
        return customers_df, accounts_df, transactions_df
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found: {e}")
    except Exception as e:
        raise Exception(f"Error loading CSV data: {e}")


def load_config():
    # 1. Start at this file's directory (src/)
    # 2. Go up one level (..) to starter/
    # 3. Enter the config folder (config/)
    # 4. Find models.yaml
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'models.yaml')
    
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def load_yaml(filename):
    """Generic helper to load any yaml file from the config folder."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', filename)
    
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
            
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Check if '{filename}' exists in the config folder.")
        
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {filename}: {e}")
        raise ValueError(f"The YAML file '{filename}' is malformed.")
        
def get_prompt(agent_key):
    """Fetch specific prompts for a given agent."""
    prompts = load_yaml('prompts.yaml')
    return prompts.get(agent_key, {})

def get_model_strategy():
    config = load_config()
    return {
        "agents": config.get("agents", {}),
        "tiers":  config.get("tiers",  {})
    }

def get_system_settings():
    config = load_config()
    return config.get("settings", {})

if __name__ == "__main__":
    print("🏗️  Foundation SAR Module")
    print("Core data schemas and utilities for SAR processing")
    print("\n📋 TODO Items:")
    print("• Implement Pydantic schemas based on CSV data")
    print("• Create ExplainabilityLogger for audit trails")
    print("• Build DataLoader for case object creation")
    print("• Add comprehensive error handling")
    print("• Write unit tests for all components")
