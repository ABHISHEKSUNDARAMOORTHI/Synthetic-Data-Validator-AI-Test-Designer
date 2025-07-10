# synthetic-validator/utils/file_utils.py

import os
import pandas as pd
import json
from io import StringIO, BytesIO
from dotenv import load_dotenv # For loading .env at the app's entry point
import streamlit as st # For Streamlit's file_uploader object and st.error/warning
from utils.logging_utils import log_message # Import custom logging utility

# --- API Key Utility (for general access, assumes load_dotenv is called elsewhere) ---
def get_gemini_api_key():
    """
    Loads the Gemini API key from environment variables.
    Assumes load_dotenv() has already been called at the application's entry point (e.g., app.py).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log_message('warning', "GEMINI_API_KEY not found in environment variables.")
    return api_key

# --- Data Loading Utilities ---
def load_data_from_uploaded_file(uploaded_file) -> pd.DataFrame:
    """
    Loads data from an uploaded Streamlit file (CSV or JSON) into a Pandas DataFrame.

    Args:
        uploaded_file: A Streamlit UploadedFile object.

    Returns:
        pd.DataFrame: The loaded DataFrame, or an empty DataFrame if loading fails.
    """
    if uploaded_file is None:
        return pd.DataFrame()

    file_name = uploaded_file.name
    file_type = file_name.split('.')[-1].lower()
    
    log_message('info', f"File_Utils: Attempting to load data from {file_name} ({file_type}).")

    try:
        if file_type == 'csv':
            # Decode as UTF-8 string to handle various CSV encodings
            string_data = StringIO(uploaded_file.getvalue().decode('utf-8'))
            df = pd.read_csv(string_data)
        elif file_type == 'json':
            # Read JSON data
            json_data = json.loads(uploaded_file.getvalue().decode('utf-8'))
            # Attempt to convert to DataFrame, assuming list of dicts or single dict
            if isinstance(json_data, list):
                df = pd.DataFrame(json_data)
            elif isinstance(json_data, dict):
                df = pd.DataFrame([json_data]) # Wrap single object in a list
            else:
                raise ValueError("Unsupported JSON structure. Expected a list of objects or a single object.")
        else:
            raise ValueError(f"Unsupported file type: {file_type}. Only CSV and JSON are supported.")
        
        log_message('info', f"File_Utils: Successfully loaded {len(df)} rows from {file_name}.")
        return df
    except Exception as e:
        log_message('error', f"File_Utils: Error loading data from {file_name}: {e}", exc_info=True)
        st.error(f"Error loading data from {file_name}: {e}. Please check your file format.")
        return pd.DataFrame()

def get_dataframe_schema_and_sample(df: pd.DataFrame, sample_rows: int = 3) -> dict:
    """
    Infers schema (column names, types) and extracts a sample of rows from a DataFrame.
    This is used to provide context to the LLM without sending the full dataset.

    Args:
        df (pd.DataFrame): The DataFrame to analyze.
        sample_rows (int): Number of sample rows to extract.

    Returns:
        dict: A dictionary containing schema and sample data.
              Example: {
                  "columns": [{"name": "col1", "type": "int64"}, ...],
                  "sample_data": [{"col1": 1, "col2": "A"}, ...]
              }
    """
    if df.empty:
        return {"columns": [], "sample_data": []}

    columns_info = []
    for col in df.columns:
        columns_info.append({
            "name": col,
            "type": str(df[col].dtype) # Convert dtype to string for serialization
        })
    
    # Convert sample rows to JSON-serializable format (list of dicts)
    sample_data = df.head(sample_rows).to_dict(orient='records')
    
    # Ensure sample data is JSON serializable (e.g., convert numpy types, datetime)
    serializable_sample_data = []
    for row in sample_data:
        serializable_row = {}
        for k, v in row.items():
            # Convert numpy types to Python native types for JSON serialization
            if pd.api.types.is_integer_dtype(type(v)):
                serializable_row[k] = int(v)
            elif pd.api.types.is_float_dtype(type(v)):
                serializable_row[k] = float(v)
            elif pd.api.types.is_bool_dtype(type(v)):
                serializable_row[k] = bool(v)
            elif pd.api.types.is_datetime64_any_dtype(type(v)):
                serializable_row[k] = str(v) # Convert datetime to string
            else:
                serializable_row[k] = v
        serializable_sample_data.append(serializable_row)

    return {
        "columns": columns_info,
        "sample_data": serializable_sample_data
    }