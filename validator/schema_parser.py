# synthetic-validator/validator/schema_parser.py

import yaml
import json
from io import StringIO
from jsonschema import validate, ValidationError, SchemaError # For schema validation
from utils.logging_utils import log_message # Import custom logging utility
import streamlit as st # For st.error/warning in UI

def load_schema_from_uploaded_file(uploaded_file) -> dict:
    """
    Loads a schema from an uploaded YAML or JSON file.

    Args:
        uploaded_file: A Streamlit UploadedFile object.

    Returns:
        dict: The loaded schema as a dictionary, or an empty dict if loading fails.
    """
    if uploaded_file is None:
        return {}

    file_name = uploaded_file.name
    file_type = file_name.split('.')[-1].lower()
    
    log_message('info', f"Schema_Parser: Attempting to load schema from {file_name} ({file_type}).")

    try:
        content = uploaded_file.getvalue().decode('utf-8')
        if file_type in ['yaml', 'yml']:
            schema = yaml.safe_load(content)
        elif file_type == 'json':
            schema = json.loads(content)
        else:
            raise ValueError(f"Unsupported schema file type: {file_type}. Only YAML/YML and JSON are supported.")
        
        # Basic validation of the schema structure itself (e.g., it's a dict)
        if not isinstance(schema, dict):
            raise ValueError("Invalid schema content: Expected a dictionary/object at the root.")

        log_message('info', f"Schema_Parser: Successfully loaded schema from {file_name}.")
        return schema
    except Exception as e:
        log_message('error', f"Schema_Parser: Error loading schema from {file_name}: {e}", exc_info=True)
        st.error(f"Error loading schema from {file_name}: {e}. Please ensure it's a valid YAML or JSON schema.")
        return {}

def validate_schema_structure(schema: dict) -> bool:
    """
    Performs a basic structural validation of the loaded schema against a common JSON Schema draft.
    This helps catch malformed schemas early.

    Args:
        schema (dict): The loaded schema dictionary.

    Returns:
        bool: True if the schema passes basic structural validation, False otherwise.
    """
    if not schema:
        log_message('warning', "Schema_Parser: No schema provided for structural validation.")
        return False

    # A very basic JSON Schema meta-schema for structural validation.
    # This checks for common top-level keywords.
    # For more rigorous validation, you might use a specific draft meta-schema.
    meta_schema = {
        "type": "object",
        "properties": {
            "$schema": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "type": {"type": "string", "enum": ["object"]},
            "properties": {"type": "object", "minProperties": 1},
            "required": {"type": "array", "items": {"type": "string"}},
            "additionalProperties": {"type": "boolean"}
        },
        "required": ["type", "properties"] # A minimal requirement for a data contract schema
    }

    try:
        validate(instance=schema, schema=meta_schema)
        log_message('info', "Schema_Parser: Schema passed basic structural validation.")
        return True
    except ValidationError as e:
        log_message('error', f"Schema_Parser: Schema structural validation failed (ValidationError): {e.message} at {e.path}", exc_info=True)
        st.error(f"Schema structural error: {e.message} (Path: {'/'.join(map(str, e.path))}). Please fix your schema file.")
        return False
    except SchemaError as e:
        log_message('error', f"Schema_Parser: Meta-schema itself is invalid (SchemaError): {e}", exc_info=True)
        st.error(f"Internal error: The schema parser's meta-schema is invalid. Please report this issue.")
        return False
    except Exception as e:
        log_message('error', f"Schema_Parser: An unexpected error occurred during schema structural validation: {e}", exc_info=True)
        st.error(f"An unexpected error occurred during schema validation: {e}")
        return False

def extract_schema_properties(schema: dict) -> dict:
    """
    Extracts and flattens key properties (name, type, format, enum, required) from a JSON Schema.
    This simplifies access for data validation and AI prompting.

    Args:
        schema (dict): The loaded schema dictionary.

    Returns:
        dict: A dictionary where keys are property names and values are their extracted details.
              Example: {
                  "field_name": {
                      "type": "string",
                      "format": "email",
                      "enum": ["value1", "value2"],
                      "required": True,
                      "description": "..."
                  },
                  ...
              }
    """
    extracted_properties = {}
    if not schema or 'properties' not in schema or not isinstance(schema['properties'], dict):
        log_message('warning', "Schema_Parser: No 'properties' found in schema or it's not a dictionary.")
        return extracted_properties

    required_fields = set(schema.get('required', []))

    for prop_name, prop_details in schema['properties'].items():
        details = {
            "type": prop_details.get('type'),
            "format": prop_details.get('format'),
            "enum": prop_details.get('enum'),
            "required": prop_name in required_fields,
            "description": prop_details.get('description'),
            "minimum": prop_details.get('minimum'),
            "maximum": prop_details.get('maximum'),
            "minLength": prop_details.get('minLength'),
            "maxLength": prop_details.get('maxLength'),
            "pattern": prop_details.get('pattern'),
            "nullable": prop_details.get('nullable', False), # Default to False if not specified
            # Add other relevant JSON Schema keywords as needed
        }
        extracted_properties[prop_name] = {k: v for k, v in details.items() if v is not None} # Filter out None values
    
    log_message('info', f"Schema_Parser: Extracted {len(extracted_properties)} properties from schema.")
    return extracted_properties