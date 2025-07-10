# synthetic-validator/reports/export_utils.py

import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any, Union

from utils.logging_utils import log_message

def generate_markdown_report(
    contract_schema: Dict[str, Any],
    synthetic_data_info: Dict[str, Any], # Schema and sample from synthetic data
    validation_report: Dict[str, Any],
    ai_suggestions_test_cases: List[Dict[str, Any]],
    ai_suggestions_schema: List[Dict[str, Any]],
    ai_patched_schema: Dict[str, Any] = None,
    user_prompt_for_test_cases: str = ""
) -> str:
    """
    Generates a comprehensive Markdown report summarizing the validation process,
    results, and AI suggestions.

    Args:
        contract_schema (Dict): The original JSON schema contract.
        synthetic_data_info (Dict): Schema and sample data extracted from the synthetic data.
        validation_report (Dict): The validation report from DataChecker.
        ai_suggestions_test_cases (List): AI-generated suggestions for test case improvements.
        ai_suggestions_schema (List): AI-generated suggestions for schema improvements.
        ai_patched_schema (Dict, optional): The AI-generated patched schema, if available. Defaults to None.
        user_prompt_for_test_cases (str): The user's prompt if test cases were AI-generated.

    Returns:
        str: The full report content in Markdown format.
    """
    log_message('info', "Export_Utils: Generating Markdown report.")

    report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_md = f"# Synthetic Data Contract Validation Report\n\n"
    report_md += f"**Generated On:** {report_timestamp}\n"
    report_md += f"**Overall Validation Status:** **{validation_report.get('overall_status', 'UNKNOWN')}**\n\n"

    # --- Section: Input Data & Schema ---
    report_md += "## 1. Input Data & Schema\n\n"
    report_md += "### Contract Schema (YAML/JSON)\n"
    report_md += "```json\n"
    report_md += json.dumps(contract_schema, indent=2)
    report_md += "\n```\n\n"

    report_md += "### Synthetic Data Info\n"
    report_md += f"- **Columns:** {len(synthetic_data_info.get('columns', []))}\n"
    report_md += f"- **Sample Data (first {len(synthetic_data_info.get('sample_data', []))} rows):**\n"
    report_md += "```json\n"
    report_md += json.dumps(synthetic_data_info.get('sample_data', []), indent=2)
    report_md += "\n```\n\n"
    
    if user_prompt_for_test_cases:
        report_md += "### AI-Generated Test Data Prompt\n"
        report_md += f"```\n{user_prompt_for_test_cases}\n```\n\n"


    # --- Section: Validation Results ---
    report_md += "## 2. Validation Results\n\n"
    report_md += f"### Overall Status: **{validation_report.get('overall_status', 'UNKNOWN')}**\n\n"

    if validation_report.get('errors'):
        report_md += "### 🛑 Errors\n"
        for i, error in enumerate(validation_report['errors']):
            report_md += f"**{i+1}. Error in Row {error.get('row_index', 'N/A')} (Path: `{error.get('path', 'N/A')}`):**\n"
            report_md += f"- Message: {error.get('message', 'N/A')}\n"
            report_md += f"- Validator: `{error.get('validator', 'N/A')}` (Value: `{error.get('validator_value', 'N/A')}`)\n"
            report_md += f"- Instance: `{json.dumps(error.get('instance', 'N/A'))}`\n\n"
    else:
        report_md += "### ✅ No Errors Detected\n\n"

    if validation_report.get('warnings'):
        report_md += "### ⚠️ Warnings\n"
        for i, warning in enumerate(validation_report['warnings']):
            report_md += f"**{i+1}. Warning for Field `{warning.get('field', 'N/A')}`:**\n"
            report_md += f"- Message: {warning.get('message', 'N/A')}\n\n"
    else:
        report_md += "### No Warnings\n\n"

    # --- Section: Coverage Analysis ---
    report_md += "## 3. Coverage Analysis\n\n"
    coverage = validation_report.get('coverage', {})

    required_coverage = coverage.get('required_fields_coverage', {})
    report_md += "### Required Fields Coverage\n"
    report_md += f"- Total Required: **{required_coverage.get('total', 0)}**\n"
    report_md += f"- Covered: **{required_coverage.get('covered', 0)}**\n"
    if required_coverage.get('missing'):
        report_md += f"- Missing/Null in Data: `{', '.join(required_coverage['missing'])}`\n"
    report_md += "\n"

    enum_coverage = coverage.get('enum_coverage', {})
    if enum_coverage:
        report_md += "### Enum Value Coverage\n"
        for field, cov_details in enum_coverage.items():
            report_md += f"- **Field `{field}`:** Total: {cov_details.get('total')}, Covered: {cov_details.get('covered')}\n"
            if cov_details.get('missing'):
                report_md += f"  - Missing Enum Values: `{', '.join(map(str, cov_details['missing']))}`\n"
        report_md += "\n"
    else:
        report_md += "### No Enum Fields or Enum Coverage Data\n\n"

    min_max_coverage = coverage.get('min_max_coverage', {})
    if min_max_coverage:
        report_md += "### Min/Max Boundary Coverage (Numeric Fields)\n"
        for field, cov_details in min_max_coverage.items():
            report_md += f"- **Field `{field}`:**\n"
            report_md += f"  - Schema Min/Max: [{cov_details.get('min_constraint', 'N/A')}, {cov_details.get('max_constraint', 'N/A')}]\n"
            report_md += f"  - Data Min/Max: [{cov_details.get('min_data_value', 'N/A')}, {cov_details.get('max_data_value', 'N/A')}]\n"
            report_md += f"  - Min Boundary Tested: {'✅' if cov_details.get('min_boundary_tested') else '❌'}\n"
            report_md += f"  - Max Boundary Tested: {'✅' if cov_details.get('max_boundary_tested') else '❌'}\n"
        report_md += "\n"
    else:
        report_md += "### No Numeric Fields with Min/Max Constraints or Coverage Data\n\n"


    # --- Section: AI Suggestions ---
    report_md += "## 4. AI Suggestions\n\n"

    if ai_suggestions_test_cases:
        report_md += "### AI-Suggested Test Case Improvements\n"
        for i, suggestion in enumerate(ai_suggestions_test_cases):
            report_md += f"**{i+1}. Field `{suggestion.get('field', 'N/A')}` ({suggestion.get('issue_type', 'N/A')}):**\n"
            report_md += f"- Recommended Value: `{json.dumps(suggestion.get('recommended_value'))}`\n"
            report_md += f"- Explanation: {suggestion.get('explanation', 'N/A')}\n\n"
    else:
        report_md += "### No AI Suggestions for Test Cases\n\n"

    if ai_suggestions_schema:
        report_md += "### AI-Suggested Schema Improvements\n"
        for i, suggestion in enumerate(ai_suggestions_schema):
            report_md += f"**{i+1}. Path `{suggestion.get('schema_path', 'N/A')}` ({suggestion.get('improvement_type', 'N/A')}):**\n"
            report_md += f"- Suggested Snippet:\n```json\n{suggestion.get('suggested_snippet', 'N/A')}\n```\n"
            report_md += f"- Explanation: {suggestion.get('explanation', 'N/A')}\n\n"
    else:
        report_md += "### No AI Suggestions for Schema\n\n"

    if ai_patched_schema:
        report_md += "### AI-Patched Schema Suggestion\n"
        report_md += "```json\n"
        report_md += json.dumps(ai_patched_schema, indent=2)
        report_md += "\n```\n\n"
    else:
        report_md += "### No AI-Patched Schema Suggestion\n\n"

    log_message('info', "Export_Utils: Markdown report generated successfully.")
    return report_md

def export_failed_cases_csv(data_df: pd.DataFrame, validation_errors: List[Dict[str, Any]]) -> Union[bytes, None]:
    """
    Exports rows from the original DataFrame that caused validation errors to a CSV format.

    Args:
        data_df (pd.DataFrame): The original synthetic data DataFrame.
        validation_errors (List[Dict]): A list of error dictionaries from the validation report.

    Returns:
        bytes: The CSV content as bytes, or None if no errors or data.
    """
    if data_df.empty or not validation_errors:
        log_message('warning', "Export_Utils: No data or validation errors to export to CSV.")
        return None

    error_indices = sorted(list(set([err['row_index'] for err in validation_errors if 'row_index' in err])))
    
    if not error_indices:
        log_message('info', "Export_Utils: No rows with specific indices found in validation errors for CSV export.")
        return None

    failed_df = data_df.iloc[error_indices]
    
    log_message('info', f"Export_Utils: Exporting {len(failed_df)} failed rows to CSV.")
    return failed_df.to_csv(index=False).encode('utf-8')

def export_ai_generated_test_cases_csv(test_cases: List[Dict[str, Any]]) -> Union[bytes, None]:
    """
    Exports AI-generated test cases to a CSV format.

    Args:
        test_cases (List[Dict]): A list of dictionaries, each representing an AI-generated test case.

    Returns:
        bytes: The CSV content as bytes, or None if no test cases.
    """
    if not test_cases:
        log_message('warning', "Export_Utils: No AI-generated test cases to export to CSV.")
        return None

    try:
        df_test_cases = pd.DataFrame(test_cases)
        log_message('info', f"Export_Utils: Exporting {len(df_test_cases)} AI-generated test cases to CSV.")
        return df_test_cases.to_csv(index=False).encode('utf-8')
    except Exception as e:
        log_message('error', f"Export_Utils: Error exporting AI-generated test cases to CSV: {e}", exc_info=True)
        return None