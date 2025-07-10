# synthetic-validator/validator/data_checker.py

import pandas as pd
from jsonschema import validate, ValidationError
from utils.logging_utils import log_message
import json
import numpy as np

class DataChecker:
    def __init__(self):
        log_message('info', "Data_Checker: Initialized DataChecker.")

    def _to_json_serializable(self, obj):
        """
        Recursively converts non-JSON-serializable types to JSON-compatible types.
        Handles numpy types, Pandas NaT/NaN, Pandas Series/DataFrames, and nested structures.
        """
        if isinstance(obj, dict):
            return {k: self._to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_json_serializable(elem) for elem in obj]
        elif isinstance(obj, pd.Series):
            # Convert Series to list and then recursively process elements
            return [self._to_json_serializable(val) for val in obj.tolist()]
        elif isinstance(obj, pd.DataFrame):
            # Convert DataFrame to list of dicts and then recursively process
            return self._convert_dataframe_to_json_serializable(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        elif pd.isna(obj): # This check is now only reached for scalar values
            return None
        else:
            # Fallback for other types that might not be directly serializable
            try:
                json.dumps(obj) # Test if it's already serializable
                return obj
            except TypeError:
                return str(obj) # Convert to string if not serializable

    def _convert_dataframe_to_json_serializable(self, df: pd.DataFrame) -> list:
        """
        Converts a Pandas DataFrame to a list of dictionaries, ensuring all values
        are JSON-serializable.
        """
        records = df.to_dict(orient='records')
        serializable_records = []
        for record in records:
            serializable_records.append(self._to_json_serializable(record))
        return serializable_records

    def validate_data_against_schema(self, data_df: pd.DataFrame, schema: dict) -> dict:
        """
        Validates the synthetic data (DataFrame) against the provided JSON Schema contract.
        """
        log_message('info', "Data_Checker: Starting data validation against schema.")
        validation_report = {
            "overall_status": "PASS",
            "errors": [],
            "warnings": [],
            "coverage": {
                "required_fields_coverage": {"total": 0, "covered": 0, "missing": []},
                "enum_coverage": {},
                "min_max_coverage": {}
            }
        }

        if data_df.empty:
            validation_report["overall_status"] = "WARNINGS"
            validation_report["warnings"].append({"message": "No data provided for validation."})
            log_message('warning', "Data_Checker: No data provided for validation.")
            return validation_report
        
        if not schema:
            validation_report["overall_status"] = "FAIL"
            validation_report["errors"].append({"message": "No schema provided for validation."})
            log_message('error', "Data_Checker: No schema provided for validation.")
            return validation_report

        # Convert DataFrame to JSON-serializable list of dicts for jsonschema validation
        data_to_validate = self._convert_dataframe_to_json_serializable(data_df)

        # --- 1. Schema Validation (Type, Format, Required, Constraints) ---
        log_message('info', "Data_Checker: Performing JSON Schema validation.")
        for i, record in enumerate(data_to_validate):
            try:
                validate(instance=record, schema=schema)
            except ValidationError as e:
                validation_report["overall_status"] = "FAIL"
                validation_report["errors"].append(self._to_json_serializable({
                    "row_index": i,
                    "path": str(e.path),
                    "message": e.message,
                    "validator": e.validator,
                    "validator_value": e.validator_value,
                    "instance": e.instance # The value that failed validation
                }))
                log_message('warning', f"Data_Checker: Validation error at row {i}: {e.message}")
            except Exception as e:
                validation_report["overall_status"] = "FAIL"
                validation_report["errors"].append(self._to_json_serializable({
                    "row_index": i,
                    "path": "N/A",
                    "message": f"Unexpected error during validation: {e}",
                    "detail": str(e)
                }))
                log_message('error', f"Data_Checker: Unexpected error during validation at row {i}: {e}", exc_info=True)

        # --- 2. Constraint Coverage Checker ---
        log_message('info', "Data_Checker: Performing constraint coverage checks.")
        
        required_fields_in_schema = set(schema.get('required', []))
        present_required_fields = set()
        
        enum_values_in_schema = {}
        enum_values_in_data = {}

        min_max_constraints = {}
        min_max_data_values = {}

        if 'properties' in schema and isinstance(schema['properties'], dict):
            for prop_name, prop_details in schema['properties'].items():
                if 'enum' in prop_details:
                    # Ensure schema enum values are serializable
                    enum_values_in_schema[prop_name] = set(self._to_json_serializable(prop_details['enum']))
                    enum_values_in_data[prop_name] = set()
                
                if 'minimum' in prop_details or 'maximum' in prop_details:
                    min_max_constraints[prop_name] = {
                        'minimum': self._to_json_serializable(prop_details.get('minimum')),
                        'maximum': self._to_json_serializable(prop_details.get('maximum'))
                    }
                    min_max_data_values[prop_name] = {
                        'min_data': float('inf'),
                        'max_data': float('-inf')
                    }
        
        for col in data_df.columns:
            if col in required_fields_in_schema:
                if not data_df[col].isnull().all():
                    present_required_fields.add(col)
            
            if col in enum_values_in_schema:
                # Convert unique values from data to serializable before adding to set
                enum_values_in_data[col].update([self._to_json_serializable(val) for val in data_df[col].dropna().unique().tolist()])

            if col in min_max_constraints and pd.api.types.is_numeric_dtype(data_df[col]):
                if not data_df[col].empty:
                    min_max_data_values[col]['min_data'] = min(min_max_data_values[col]['min_data'], self._to_json_serializable(data_df[col].min()))
                    min_max_data_values[col]['max_data'] = max(min_max_data_values[col]['max_data'], self._to_json_serializable(data_df[col].max()))
        
        # Consolidate required fields coverage
        missing_required_fields = list(required_fields_in_schema - present_required_fields)
        validation_report["coverage"]["required_fields_coverage"] = {
            "total": len(required_fields_in_schema),
            "covered": len(present_required_fields),
            "missing": missing_required_fields
        }
        if missing_required_fields:
            validation_report["overall_status"] = "WARNINGS"
            validation_report["warnings"].append({
                "field": "N/A",
                "message": f"Missing or entirely null required fields: {', '.join(missing_required_fields)}."
            })

        # Consolidate enum coverage
        for field, schema_enums in enum_values_in_schema.items():
            data_enums = enum_values_in_data.get(field, set())
            missing_enum_values = list(schema_enums - data_enums)
            validation_report["coverage"]["enum_coverage"][field] = {
                "total": len(schema_enums),
                "covered": len(data_enums),
                "missing": missing_enum_values
            }
            if missing_enum_values:
                validation_report["overall_status"] = "WARNINGS"
                validation_report["warnings"].append({
                    "field": field,
                    "message": f"Enum values in schema not present in data for '{field}': {', '.join(map(str, missing_enum_values))}."
                })

        # Consolidate min/max coverage
        for field, constraints in min_max_constraints.items():
            data_values = min_max_data_values.get(field)
            if data_values and data_values['min_data'] != float('inf') and data_values['max_data'] != float('-inf'):
                min_constraint_val = constraints['minimum']
                max_constraint_val = constraints['maximum']
                min_data_val = data_values['min_data']
                max_data_val = data_values['max_data']

                tolerance = 0.01 * (max_constraint_val - min_constraint_val) if min_constraint_val is not None and max_constraint_val is not None else 0.01
                
                min_boundary_tested = (min_constraint_val is None) or \
                                      (min_data_val <= min_constraint_val + tolerance and min_data_val >= min_constraint_val - tolerance)
                max_boundary_tested = (max_constraint_val is None) or \
                                      (max_data_val >= max_constraint_val - tolerance and max_data_val <= max_constraint_val + tolerance)

                validation_report["coverage"]["min_max_coverage"][field] = {
                    "min_constraint": min_constraint_val,
                    "max_constraint": max_constraint_val,
                    "min_data_value": min_data_val,
                    "max_data_value": max_data_val,
                    "min_boundary_tested": min_boundary_tested,
                    "max_boundary_tested": max_boundary_tested
                }
                if min_constraint_val is not None and not min_boundary_tested:
                     validation_report["overall_status"] = "WARNINGS"
                     validation_report["warnings"].append({
                         "field": field,
                         "message": f"Data for '{field}' does not sufficiently test the minimum boundary ({min_constraint_val}). Smallest value found: {min_data_val:.2f}."
                     })
                if max_constraint_val is not None and not max_boundary_tested:
                     validation_report["overall_status"] = "WARNINGS"
                     validation_report["warnings"].append({
                         "field": field,
                         "message": f"Data for '{field}' does not sufficiently test the maximum boundary ({max_constraint_val}). Largest value found: {max_data_val:.2f}."
                     })
            else:
                if (constraints['minimum'] is not None or constraints['maximum'] is not None) and \
                   (data_values['min_data'] == float('inf') or data_values['max_data'] == float('-inf')):
                    validation_report["overall_status"] = "WARNINGS"
                    validation_report["warnings"].append({
                        "field": field,
                        "message": f"Min/Max constraints for '{field}' defined in schema but no numeric data found to test them."
                    })
        
        final_report = self._to_json_serializable(validation_report)
        log_message('info', f"Data_Checker: Data validation completed with status: {final_report['overall_status']}.")
        return final_report