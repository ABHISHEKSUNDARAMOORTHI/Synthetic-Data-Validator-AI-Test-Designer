# synthetic-validator/validator/test_case_generator.py

import google.generativeai as genai
import os
import json
import logging
import time
import random
import pandas as pd # To convert generated data to DataFrame
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
        log_message('error', "Test_Case_Generator: GEMINI_API_KEY not found in environment variables during model configuration.")
        raise ValueError("GEMINI_API_KEY is not set. Cannot initialize AI models.")
    
    genai.configure(api_key=api_key)
    
    try:
        log_message('info', "Test_Case_Generator: Attempting to initialize text generation model: models/gemini-1.5-flash-latest")
        text_gen_model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        log_message('info', "Test_Case_Generator: Gemini text generation model initialized successfully.")
    except Exception as e:
        log_message('error', f"Test_Case_Generator: Failed to initialize Gemini text generation model: {e}", exc_info=True)
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
        log_message('error', f"Test_Case_Generator: JSON decoding failed: {e}. Raw response: {cleaned_text[:500]}...")
        raise ValueError(f"Failed to parse JSON response from AI: {e}")
    except Exception as e:
        log_message('error', f"Test_Case_Generator: An unexpected error occurred during JSON parsing: {e}", exc_info=True)
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
            log_message('info', f"Test_Case_Generator: API Call Attempt {retry_count + 1}/{MAX_RETRIES}.")
            response = model_instance.generate_content(prompt)
            return response.text
        
        except ResourceExhausted as e: # This is the 429 quota error
            retry_count += 1
            if retry_count == MAX_RETRIES:
                log_message('error', f"Test_Case_Generator: Max retries reached for ResourceExhausted. Last error: {e}")
                raise e # Re-raise the quota error if max retries reached

            wait_time = INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, RETRY_JITTER_MAX)
            log_message('warning', f"Test_Case_Generator: Quota exceeded (429) on attempt {retry_count}. Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        except (InternalServerError, GoogleAPIError) as e: # Catch other API-related errors
            retry_count += 1
            log_message('error', f"Test_Case_Generator: API error (non-quota) on attempt {retry_count}/{MAX_RETRIES}: {e}", exc_info=True)
            if retry_count == MAX_RETRIES:
                raise e
            wait_time = INITIAL_RETRY_DELAY * (2 ** (retry_count - 1)) + random.uniform(0, RETRY_JITTER_MAX)
            log_message('warning', f"Test_Case_Generator: API error. Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        except Exception as e: # Catch any other general exceptions
            log_message('error', f"Test_Case_Generator: An unexpected error occurred during Gemini API call on attempt {retry_count + 1}: {e}", exc_info=True)
            raise e # Re-raise immediately for other error types
    
    raise Exception("Test_Case_Generator: API call failed after multiple retries for an unknown reason.")


# --- Public AI Functions for Test Case Generation ---

def generate_synthetic_test_cases(
    schema: Dict[str, Any],
    num_cases: int = 5,
    focus_on_issues: List[Dict[str, Any]] = None, # From validation_report.errors/warnings
    specific_instructions: str = ""
) -> Dict[str, Any]:
    """
    Uses Gemini to generate synthetic test data based on a JSON schema,
    optionally focusing on specific issues or instructions.

    Args:
        schema (Dict): The JSON schema contract.
        num_cases (int): The desired number of test cases to generate.
        focus_on_issues (List[Dict]): A list of issues (errors/warnings) from a validation report
                                       to guide the generation towards problematic areas.
        specific_instructions (str): Any additional instructions for the AI, e.g., "ensure all enum values are present".

    Returns:
        Dict[str, Any]: A dictionary containing generated test cases (as a list of dicts)
                        and an optional error message.
                        Example: {"test_cases": [{"field1": "value1"}, {...}], "error": "..."}
    """
    if not text_gen_model:
        return {"test_cases": [], "error": "AI model not initialized. Check API key."}
    if not schema:
        return {"test_cases": [], "error": "Schema is missing for test case generation."}

    schema_str = json.dumps(schema, indent=2)
    
    issue_context = ""
    if focus_on_issues:
        issue_context = "\nFocus on these specific issues from a validation report:\n"
        for issue in focus_on_issues[:5]: # Limit context to avoid long prompts
            issue_context += f"- Field: {issue.get('field', 'N/A')}, Message: {issue.get('message', 'N/A')}, Path: {issue.get('path', 'N/A')}\n"
        issue_context += "\nGenerate data that specifically tests these problematic areas, including edge cases."

    instructions_context = ""
    if specific_instructions:
        instructions_context = f"\nAdditional instructions: {specific_instructions}\n"

    prompt = f"""
    You are an AI assistant specialized in generating synthetic test data for data validation.
    Given the following JSON schema contract, generate {num_cases} synthetic data records.
    Each record should adhere to the schema.
    
    {issue_context}
    {instructions_context}

    Ensure the generated data includes a variety of valid values, including:
    - Typical values.
    - Boundary values (e.g., min/max for numbers, minLength/maxLength for strings).
    - All possible enum values (if applicable and reasonable for {num_cases} cases).
    - Null values where the schema allows (e.g., "nullable": true or not "required").
    - Values that test different formats (e.g., "date-time", "email", "uuid").

    Return the generated data as a JSON array of objects, where each object represents one record.
    Do NOT include any additional text or markdown outside the JSON array.

    JSON Schema Contract:
    ```json
    {schema_str}
    ```
    """
    
    try:
        log_message('info', f"Test_Case_Generator: Requesting {num_cases} synthetic test cases from Gemini.")
        response_text = _call_gemini_with_retry(text_gen_model, prompt)
        parsed_response = _parse_gemini_json_response(response_text)
        
        if not isinstance(parsed_response, list):
            raise ValueError("AI returned an unexpected JSON structure for test cases (expected a list of objects).")
            
        return {"test_cases": parsed_response, "error": None}
    except Exception as e:
        log_message('error', f"Test_Case_Generator: Error generating synthetic test cases: {e}", exc_info=True)
        return {"test_cases": [], "error": f"Failed to generate test cases: {e}"}

def reverse_engineer_schema_from_data(
    sample_data_df: pd.DataFrame,
    num_samples_for_analysis: int = 100 # Use a subset for large DFs
) -> Dict[str, Any]:
    """
    Uses Gemini to reverse-engineer a JSON schema from sample data.
    This is useful if a schema is missing or incomplete.

    Args:
        sample_data_df (pd.DataFrame): A DataFrame containing sample data.
        num_samples_for_analysis (int): Number of rows to sample for AI analysis.

    Returns:
        Dict[str, Any]: A dictionary containing the generated JSON schema or an error.
                        Example: {"schema": {...}, "error": "..."}
    """
    if not text_gen_model:
        return {"schema": {}, "error": "AI model not initialized. Check API key."}
    if sample_data_df.empty:
        return {"schema": {}, "error": "No sample data provided for schema reverse-engineering."}

    # Take a sample of the data to keep prompt size manageable
    data_sample = sample_data_df.head(num_samples_for_analysis).to_dict(orient='records')
    data_sample_str = json.dumps(data_sample, indent=2)

    prompt = f"""
    You are an AI assistant specialized in inferring JSON Schemas from sample data.
    Given the following sample data, generate a comprehensive JSON Schema (Draft 7 compatible)
    that accurately describes the structure, data types, and potential constraints
    (e.g., required fields, formats, enums, min/max for numbers, minLength/maxLength for strings).

    Consider the following when generating the schema:
    - Infer appropriate JSON Schema types (string, number, integer, boolean, array, object, null).
    - Identify 'required' fields based on their consistent presence.
    - Infer 'format' for strings (e.g., "date-time", "email", "uuid") if patterns are evident.
    - Infer 'enum' for fields with a limited set of discrete values.
    - Infer 'minimum' and 'maximum' for numeric fields based on observed ranges.
    - Infer 'minLength' and 'maxLength' for string fields.
    - Use 'description' to briefly explain each field.
    - If a field can be null, include `"type": ["string", "null"]` or similar.

    Sample Data:
    ```json
    {data_sample_str}
    ```

    Return the generated JSON Schema as a JSON object. Do NOT include any additional text or markdown outside the JSON object.
    """
    
    try:
        log_message('info', "Test_Case_Generator: Requesting schema reverse-engineering from Gemini.")
        response_text = _call_gemini_with_retry(text_gen_model, prompt)
        parsed_response = _parse_gemini_json_response(response_text)
        
        if not isinstance(parsed_response, dict):
            raise ValueError("AI returned an unexpected JSON structure for schema (expected an object).")
            
        return {"schema": parsed_response, "error": None}
    except Exception as e:
        log_message('error', f"Test_Case_Generator: Error reverse-engineering schema: {e}", exc_info=True)
        return {"schema": {}, "error": f"Failed to reverse-engineer schema: {e}"}