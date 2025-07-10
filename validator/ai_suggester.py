# synthetic-validator/validator/ai_suggester.py

import google.generativeai as genai
import os
import json
import logging
import time
import random
from typing import Union, List, Dict, Any
from google.api_core.exceptions import ResourceExhausted, InternalServerError, GoogleAPIError

# Import custom logging utility
from utils.logging_utils import log_message
from dotenv import load_dotenv # Ensure this is at the top

# Call load_dotenv() at the very top level of the module
load_dotenv()

# --- Retry Configuration ---
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2
RETRY_JITTER_MAX = 0.5

# --- Gemini Model Configuration ---
text_gen_model = None

def _configure_gemini_models():
    """Configures and initializes the text generation model."""
    global text_gen_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log_message('error', "AI_Suggester: GEMINI_API_KEY not found in environment variables during model configuration.")
        raise ValueError("GEMINI_API_KEY is not set. Cannot initialize AI models.")
    
    genai.configure(api_key=api_key)
    
    try:
        log_message('info', "AI_Suggester: Attempting to initialize text generation model: models/gemini-1.5-flash-latest")
        text_gen_model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        log_message('info', "AI_Suggester: Gemini text generation model initialized successfully.")
    except Exception as e:
        log_message('error', f"AI_Suggester: Failed to initialize Gemini text generation model: {e}", exc_info=True)
        text_gen_model = None
        raise # Re-raise to indicate failure to the caller


# --- Helper for parsing JSON from Gemini responses ---
def _parse_gemini_json_response(response_text: str) -> Union[Dict, List]:
    """
    Attempts to parse JSON from Gemini's text response, handling common markdown formatting.
    Returns the parsed JSON object (dict or list). Raises ValueError on parsing failure.
    """
    cleaned_text = response_text.strip()
    
    # Remove markdown code block wrappers if present
    if cleaned_text.startswith("```json") and cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[7:-3].strip()
    elif cleaned_text.startswith("```") and cleaned_text.endswith("```"): # Generic code block
        cleaned_text = cleaned_text[3:-3].strip()
    
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        log_message('error', f"AI_Suggester: JSON decoding failed: {e}. Raw response: {cleaned_text[:500]}...")
        raise ValueError(f"Failed to parse JSON response from AI: {e}")
    except Exception as e:
        log_message('error', f"AI_Suggester: An unexpected error occurred during JSON parsing: {e}", exc_info=True)
        raise ValueError(f"Unexpected error parsing AI response: {e}")


# --- Internal Gemini API Call Helper with Retry Logic ---
def _call_gemini_with_retry(model_instance: genai.GenerativeModel, prompt: str) -> str:
    """
    Internal helper to call Gemini's generate_content with retry logic.
    Returns the response text. Raises an exception if all retries fail.
    """
    if not model_instance:
        raise ValueError("Gemini model is not initialized. Cannot make API call.")

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            log_message('info', f"AI_Suggester: API Call Attempt {retry_count + 1}/{MAX_RETRIES}.")
            response = model_instance.generate_content(prompt)
            return response.text
        
        except ResourceExhausted as e: # This is the 429 quota error
            retry_count += 1
            if retry_count == MAX_RETRIES:
                log_message('error', f"AI_Suggester: Max retries reached for ResourceExhausted. Last error: {e}")
                raise e # Re-raise the quota error if max retries reached

            wait_time = INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, RETRY_JITTER_MAX)
            log_message('warning', f"AI_Suggester: Quota exceeded (429) on attempt {retry_count}. Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        except (InternalServerError, GoogleAPIError) as e: # Catch other API-related errors
            retry_count += 1
            log_message('error', f"AI_Suggester: API error (non-quota) on attempt {retry_count}/{MAX_RETRIES}: {e}", exc_info=True)
            if retry_count == MAX_RETRIES:
                raise e
            wait_time = INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, RETRY_JITTER_MAX)
            log_message('warning', f"AI_Suggester: API error. Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        except Exception as e: # Catch any other general exceptions
            log_message('error', f"AI_Suggester: An unexpected error occurred during Gemini API call on attempt {retry_count + 1}: {e}", exc_info=True)
            raise e # Re-raise immediately for other error types
    
    raise Exception("AI_Suggester: API call failed after multiple retries for an unknown reason.")


# --- Public AI Functions for Suggestions ---

def suggest_test_case_improvements(
    schema: Dict[str, Any],
    validation_report: Dict[str, Any],
    num_suggestions: int = 3
) -> Dict[str, Any]:
    """
    Uses Gemini to suggest improvements for synthetic data test cases based on validation
    errors and coverage gaps.

    Args:
        schema (Dict): The JSON schema contract.
        validation_report (Dict): The validation report from DataChecker.
        num_suggestions (int): Number of distinct suggestions to generate.

    Returns:
        Dict[str, Any]: A dictionary containing AI suggestions for test cases.
                        Example: {"suggestions": ["...", "..."], "error": "..."}
    """
    if not text_gen_model:
        return {"suggestions": [], "error": "AI model not initialized. Check API key."}
    if not schema or not validation_report:
        return {"suggestions": [], "error": "Schema or validation report missing for suggestions."}

    # Prepare a concise summary of the validation report for the LLM
    report_summary = {
        "overall_status": validation_report.get("overall_status"),
        "errors": validation_report.get("errors", [])[:5], # Limit errors for prompt
        "warnings": validation_report.get("warnings", [])[:5], # Limit warnings for prompt
        "coverage": validation_report.get("coverage", {})
    }
    
    schema_str = json.dumps(schema, indent=2)
    report_summary_str = json.dumps(report_summary, indent=2)

    prompt = f"""
    You are an AI assistant specialized in data quality and test case design.
    Given a JSON schema contract and a validation report for synthetic data against this schema,
    suggest specific improvements for the synthetic data test cases. Focus on addressing
    validation errors and improving constraint coverage.

    JSON Schema Contract:
    ```json
    {schema_str}
    ```

    Validation Report Summary:
    ```json
    {report_summary_str}
    ```

    Based on the above, provide {num_suggestions} distinct suggestions for new or modified synthetic data points.
    For each suggestion, clearly state:
    1.  The specific field(s) involved.
    2.  The type of issue it addresses (e.g., "missing required field", "enum boundary", "min/max edge case", "invalid format").
    3.  The exact value(s) or data structure change you recommend.
    4.  A brief explanation of why this test case is important.

    Return the suggestions as a JSON array of objects, where each object has keys:
    "field": (string)
    "issue_type": (string)
    "recommended_value": (any valid JSON type - string, number, boolean, object, array, null)
    "explanation": (string)
    """
    
    try:
        log_message('info', "AI_Suggester: Requesting test case suggestions from Gemini.")
        response_text = _call_gemini_with_retry(text_gen_model, prompt)
        parsed_response = _parse_gemini_json_response(response_text)
        
        if not isinstance(parsed_response, list):
            raise ValueError("AI returned an unexpected JSON structure for test case suggestions (expected a list).")
            
        return {"suggestions": parsed_response, "error": None}
    except Exception as e:
        log_message('error', f"AI_Suggester: Error suggesting test case improvements: {e}", exc_info=True)
        return {"suggestions": [], "error": f"Failed to generate test case suggestions: {e}"}


def suggest_schema_improvements(
    schema: Dict[str, Any],
    validation_report: Dict[str, Any],
    num_suggestions: int = 3
) -> Dict[str, Any]:
    """
    Uses Gemini to suggest improvements or fixes to the JSON schema contract itself,
    based on the validation report and common schema best practices.

    Args:
        schema (Dict): The current JSON schema contract.
        validation_report (Dict): The validation report from DataChecker.
        num_suggestions (int): Number of distinct suggestions to generate.

    Returns:
        Dict[str, Any]: A dictionary containing AI suggestions for schema improvements.
                        Example: {"suggestions": ["...", "..."], "error": "..."}
    """
    if not text_gen_model:
        return {"suggestions": [], "error": "AI model not initialized. Check API key."}
    if not schema or not validation_report:
        return {"suggestions": [], "error": "Schema or validation report missing for suggestions."}

    report_summary = {
        "overall_status": validation_report.get("overall_status"),
        "errors": validation_report.get("errors", [])[:5],
        "warnings": validation_report.get("warnings", [])[:5],
        "coverage": validation_report.get("coverage", {})
    }
    
    schema_str = json.dumps(schema, indent=2)
    report_summary_str = json.dumps(report_summary, indent=2)

    prompt = f"""
    You are an AI assistant specialized in JSON Schema design and data contract best practices.
    Given a JSON schema contract and a validation report for synthetic data against this schema,
    suggest specific improvements or fixes to the JSON schema itself. Focus on:
    - Adding stricter types (e.g., 'string' with 'format' like 'email', 'uuid', 'date-time').
    - Suggesting logical constraints (e.g., 'minimum', 'maximum', 'minLength', 'maxLength', 'pattern').
    - Identifying potentially missing 'required' fields.
    - Improving descriptions.
    - Adding 'enum' for fields with limited discrete values.
    - Suggesting 'if-then-else', 'anyOf', 'oneOf' for complex conditional logic.

    JSON Schema Contract:
    ```json
    {schema_str}
    ```

    Validation Report Summary:
    ```json
    {report_summary_str}
    ```

    Based on the above, provide {num_suggestions} distinct suggestions for improving the JSON schema.
    For each suggestion, clearly state:
    1.  The specific path in the schema (e.g., "properties.field_name").
    2.  The type of improvement (e.g., "add format", "add minLength", "add enum", "add required").
    3.  The suggested JSON Schema snippet to add or modify.
    4.  A brief explanation of why this improvement is beneficial.

    Return the suggestions as a JSON array of objects, where each object has keys:
    "schema_path": (string)
    "improvement_type": (string)
    "suggested_snippet": (string - a valid JSON string representing the snippet)
    "explanation": (string)
    """
    
    try:
        log_message('info', "AI_Suggester: Requesting schema improvements from Gemini.")
        response_text = _call_gemini_with_retry(text_gen_model, prompt)
        parsed_response = _parse_gemini_json_response(response_text)
        
        if not isinstance(parsed_response, list):
            raise ValueError("AI returned an unexpected JSON structure for schema suggestions (expected a list).")
            
        return {"suggestions": parsed_response, "error": None}
    except Exception as e:
        log_message('error', f"AI_Suggester: Error suggesting schema improvements: {e}", exc_info=True)
        return {"suggestions": [], "error": f"Failed to generate schema improvement suggestions: {e}"}

