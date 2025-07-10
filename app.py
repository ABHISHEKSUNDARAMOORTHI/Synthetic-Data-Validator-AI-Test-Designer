# synthetic-validator/app.py

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import altair as alt
import matplotlib.pyplot as plt # Needed for potential future custom plots/heatmaps
from dotenv import load_dotenv # For loading .env file

# Call load_dotenv() at the very top of the Streamlit app's execution
load_dotenv()

# --- Project Module Imports ---
# Utils
from utils.logging_utils import log_message
from utils.file_utils import get_gemini_api_key, load_data_from_uploaded_file, get_dataframe_schema_and_sample

# Validator
from validator.schema_parser import load_schema_from_uploaded_file, validate_schema_structure, extract_schema_properties
from validator.data_checker import DataChecker
import validator.ai_suggester as ai_suggester # Import as module to call configure and functions
import validator.test_case_generator as test_case_generator # Import as module

# Reports
from reports.export_utils import generate_markdown_report, export_failed_cases_csv, export_ai_generated_test_cases_csv

# --- App Configuration ---
st.set_page_config(page_title="Synthetic Data Validator + AI Test Designer", page_icon="🧪", layout="wide")
# Custom CSS (assuming styling.py exists and inject_custom_css is defined there)
try:
    from styling import inject_custom_css
    inject_custom_css()
    log_message('info', "App: Custom CSS injected.")
except ImportError:
    log_message('warning', "App: Could not import styling.py. Running without custom CSS.")
    pass # Continue without custom CSS if file is missing

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes Streamlit session state variables."""
    if 'contract_file' not in st.session_state: st.session_state['contract_file'] = None
    if 'synthetic_data_file' not in st.session_state: st.session_state['synthetic_data_file'] = None
    if 'contract_schema' not in st.session_state: st.session_state['contract_schema'] = {}
    if 'extracted_schema_props' not in st.session_state: st.session_state['extracted_schema_props'] = {}
    if 'synthetic_data_df' not in st.session_state: st.session_state['synthetic_data_df'] = pd.DataFrame()
    if 'synthetic_data_info' not in st.session_state: st.session_state['synthetic_data_info'] = {} # Schema & sample of synthetic data
    if 'validation_report' not in st.session_state: st.session_state['validation_report'] = None
    if 'ai_suggestions_test_cases' not in st.session_state: st.session_state['ai_suggestions_test_cases'] = []
    if 'ai_suggestions_schema' not in st.session_state: st.session_state['ai_suggestions_schema'] = []
    if 'ai_generated_test_cases_df' not in st.session_state: st.session_state['ai_generated_test_cases_df'] = pd.DataFrame()
    if 'ai_patched_schema' not in st.session_state: st.session_state['ai_patched_schema'] = {}
    if 'gemini_api_key_loaded' not in st.session_state: st.session_state['gemini_api_key_loaded'] = False
    if 'data_checker' not in st.session_state: st.session_state['data_checker'] = None
    if 'user_test_case_prompt' not in st.session_state: st.session_state['user_test_case_prompt'] = ""
    if 'ai_test_case_generation_error' not in st.session_state: st.session_state['ai_test_case_generation_error'] = None

initialize_session_state()
log_message('info', "App: Session state initialized.")


# --- Sidebar: Gemini API Configuration ---
st.sidebar.header("🔐 Gemini API Configuration")

api_key_from_env = os.getenv("GEMINI_API_KEY")

if api_key_from_env:
    st.sidebar.success("API Key loaded from .env")
    st.session_state['gemini_api_key_loaded'] = True
    # Configure AI models only if not already configured
    if not ai_suggester.text_gen_model:
        try:
            ai_suggester._configure_gemini_models()
            test_case_generator._configure_gemini_models()
            log_message('info', "App: Gemini models configured from .env key.")
        except Exception as e:
            log_message('error', f"App: Failed to configure Gemini models from .env: {e}")
            st.session_state['gemini_api_key_loaded'] = False
            st.error("🚨 Failed to initialize AI models with .env key. Please check your key or try entering it below.")
else:
    user_api_key_input = st.sidebar.text_input("Enter your Gemini API key", type="password", key="user_api_key_input")
    if user_api_key_input:
        os.environ["GEMINI_API_KEY"] = user_api_key_input
        st.session_state['gemini_api_key_loaded'] = True
        st.sidebar.success("API Key set for this session.")
        try:
            ai_suggester._configure_gemini_models()
            test_case_generator._configure_gemini_models()
            log_message('info', "App: Gemini models re-configured with user-provided API key.")
        except Exception as e:
            log_message('error', f"App: Failed to re-configure Gemini models: {e}")
            st.session_state['gemini_api_key_loaded'] = False
        st.rerun() # Rerun to apply API key and re-initialize models
    else:
        st.sidebar.info("Please provide an API key to enable AI features.")
        st.session_state['gemini_api_key_loaded'] = False

if not st.session_state['gemini_api_key_loaded']:
    st.error("🚨 Gemini API Key is missing or invalid. Please ensure your .env file is correct or enter the key in the sidebar.")

log_message('info', "App: Gemini API Key status checked.")

# --- Sidebar: AI Feature Controls ---
st.sidebar.markdown("---")
st.sidebar.subheader("AI Feature Controls (Quota-Aware)")
st.sidebar.info("Manage AI calls to conserve free-tier quota.")
st.session_state['enable_ai_suggestions_test_cases'] = st.sidebar.checkbox("Enable AI Test Case Suggestions", value=True, key="enable_ai_test_case_suggestions")
st.session_state['enable_ai_suggestions_schema'] = st.sidebar.checkbox("Enable AI Schema Improvements", value=True, key="enable_ai_schema_improvements")
st.session_state['enable_ai_test_case_generation'] = st.sidebar.checkbox("Enable AI Test Data Generation", value=True, key="enable_ai_test_data_generation")
log_message('info', "App: Sidebar AI feature controls initialized.")

# --- Initialize DataChecker ---
if st.session_state['data_checker'] is None:
    log_message('info', "App: Initializing DataChecker.")
    try:
        st.session_state['data_checker'] = DataChecker()
        log_message('info', "App: DataChecker initialized successfully.")
    except Exception as e:
        log_message('error', f"App: Failed to initialize DataChecker: {e}")
        st.error(f"Failed to initialize data validation engine: {e}. Check logs for details.")
log_message('info', "App: DataChecker status checked.")


# --- Main App Title ---
st.title("🧪 Synthetic Data Validator + AI Test Designer")
st.markdown("Automate validation, detect coverage gaps, and design better tests with AI.")
log_message('info', "App: Main title and markdown rendered.")


# --- SECTION 1: Input Contract & Data ---
st.header("1. Input Contract & Synthetic Data")
st.markdown("Upload your schema contract (YAML/JSON) and the synthetic data (CSV/JSON) to validate.")
log_message('info', "App: Section 1 header and markdown rendered.")

col1_1, col1_2 = st.columns(2)
with col1_1:
    contract_file = st.file_uploader(
        "Upload Schema Contract (YAML/JSON)",
        type=["yaml", "yml", "json"],
        key="contract_uploader"
    )
    if contract_file and contract_file != st.session_state['contract_file']:
        st.session_state['contract_file'] = contract_file
        st.session_state['contract_schema'] = load_schema_from_uploaded_file(contract_file)
        if st.session_state['contract_schema']:
            validate_schema_structure(st.session_state['contract_schema'])
            st.session_state['extracted_schema_props'] = extract_schema_properties(st.session_state['contract_schema'])
        st.session_state['validation_report'] = None # Reset validation on new schema
        st.rerun()

    if st.session_state['contract_schema']:
        st.subheader("Contract Schema Preview")
        st.json(st.session_state['contract_schema'])
        st.subheader("Extracted Schema Properties")
        st.json(st.session_state['extracted_schema_props'])
    else:
        st.info("Upload a schema contract to see its preview.")

with col1_2:
    synthetic_data_file = st.file_uploader(
        "Upload Synthetic Data (CSV/JSON)",
        type=["csv", "json"],
        key="synthetic_data_uploader"
    )
    if synthetic_data_file and synthetic_data_file != st.session_state['synthetic_data_file']:
        st.session_state['synthetic_data_file'] = synthetic_data_file
        st.session_state['synthetic_data_df'] = load_data_from_uploaded_file(synthetic_data_file)
        st.session_state['synthetic_data_info'] = get_dataframe_schema_and_sample(st.session_state['synthetic_data_df'])
        st.session_state['validation_report'] = None # Reset validation on new data
        st.rerun()

    if not st.session_state['synthetic_data_df'].empty:
        st.subheader("Synthetic Data Preview")
        st.write(f"Rows: {len(st.session_state['synthetic_data_df'])}, Columns: {len(st.session_state['synthetic_data_df'].columns)}")
        with st.expander("Expand to see full data preview"):
            st.dataframe(st.session_state['synthetic_data_df'].head(10), use_container_width=True)
        st.subheader("Synthetic Data Info (for AI context)")
        st.json(st.session_state['synthetic_data_info'])
    else:
        st.info("Upload synthetic data to see its preview.")

log_message('info', "App: Finished Section 1 rendering.")

# --- SECTION 2: Validation & AI Suggestions ---
st.header("2. Validate Data & Get AI Suggestions")
st.markdown("Run validation to check data adherence and identify coverage gaps. AI can suggest improvements.")
log_message('info', "App: Section 2 header and markdown rendered.")

if st.button("🚀 Run Validation & Get AI Insights", key="run_validation_button"):
    log_message('info', "App: 'Run Validation' button clicked.")
    if not st.session_state['contract_schema']:
        st.error("Please upload a schema contract first.")
    elif st.session_state['synthetic_data_df'].empty:
        st.error("Please upload synthetic data first.")
    elif not st.session_state['gemini_api_key_loaded']:
        st.error("Gemini API key not loaded. Please provide it in the sidebar to use AI features.")
    else:
        st.session_state['ai_suggestions_test_cases'] = [] # Clear previous suggestions
        st.session_state['ai_suggestions_schema'] = [] # Clear previous suggestions
        st.session_state['ai_patched_schema'] = {} # Clear previous patched schema

        with st.spinner("Validating data and generating AI insights..."):
            # Run data validation
            validation_report = st.session_state['data_checker'].validate_data_against_schema(
                st.session_state['synthetic_data_df'],
                st.session_state['contract_schema']
            )
            st.session_state['validation_report'] = validation_report
            log_message('info', f"App: Data validation completed. Status: {validation_report.get('overall_status')}")

            # Get AI suggestions for test cases
            if st.session_state['enable_ai_suggestions_test_cases']:
                ai_test_case_suggestions_result = ai_suggester.suggest_test_case_improvements(
                    st.session_state['contract_schema'],
                    validation_report
                )
                if ai_test_case_suggestions_result.get('error'):
                    st.warning(f"AI Test Case Suggestions Error: {ai_test_case_suggestions_result['error']}")
                    log_message('warning', f"App: AI test case suggestions failed: {ai_test_case_suggestions_result['error']}")
                else:
                    st.session_state['ai_suggestions_test_cases'] = ai_test_case_suggestions_result['suggestions']
                    log_message('info', "App: AI test case suggestions generated.")
            else:
                log_message('info', "App: AI Test Case Suggestions disabled.")

            # Get AI suggestions for schema improvements
            if st.session_state['enable_ai_suggestions_schema']:
                ai_schema_suggestions_result = ai_suggester.suggest_schema_improvements(
                    st.session_state['contract_schema'],
                    validation_report
                )
                if ai_schema_suggestions_result.get('error'):
                    st.warning(f"AI Schema Suggestions Error: {ai_schema_suggestions_result['error']}")
                    log_message('warning', f"App: AI schema suggestions failed: {ai_schema_suggestions_result['error']}")
                else:
                    st.session_state['ai_suggestions_schema'] = ai_schema_suggestions_result['suggestions']
                    # Attempt to auto-patch schema if suggestions are simple and clear (optional, advanced)
                    # For MVP, we just display the suggestions.
                    log_message('info', "App: AI schema suggestions generated.")
            else:
                log_message('info', "App: AI Schema Improvements disabled.")
        
        st.success("Validation and AI insights generated!")
        st.rerun() # Rerun to display results

if st.session_state['validation_report']:
    st.subheader("Validation Report")
    report_status = st.session_state['validation_report'].get('overall_status', 'UNKNOWN')
    
    if report_status == "PASS":
        st.markdown("### ✅ Overall Status: **PASS**")
        st.success("Your synthetic data adheres to the schema contract with no detected errors or warnings.")
    elif report_status == "WARNINGS":
        st.markdown("### ⚠️ Overall Status: **WARNINGS**")
        st.warning("Your synthetic data has some warnings or coverage gaps. Review the details below.")
    elif report_status == "FAIL":
        st.markdown("### 🛑 Overall Status: **FAIL**")
        st.error("Your synthetic data has critical validation errors. Please review and fix the data.")
    
    with st.expander("View Detailed Report"):
        st.json(st.session_state['validation_report'])

    # Display Errors
    if st.session_state['validation_report'].get('errors'):
        st.markdown("#### 🛑 Validation Errors")
        for i, error in enumerate(st.session_state['validation_report']['errors']):
            st.error(f"**Error {i+1} (Row {error.get('row_index', 'N/A')}, Path `{error.get('path', 'N/A')}`):** {error.get('message', 'N/A')}")
            with st.expander(f"Details for Error {i+1}"):
                st.json(error)

    # Display Warnings
    if st.session_state['validation_report'].get('warnings'):
        st.markdown("#### ⚠️ Validation Warnings / Coverage Gaps")
        for i, warning in enumerate(st.session_state['validation_report']['warnings']):
            st.warning(f"**Warning {i+1} (Field `{warning.get('field', 'N/A')}`):** {warning.get('message', 'N/A')}")
            with st.expander(f"Details for Warning {i+1}"):
                st.json(warning)

    # Display Coverage Summary (simplified visuals)
    st.markdown("#### 📊 Coverage Summary")
    coverage = st.session_state['validation_report'].get('coverage', {})

    # Required Fields Coverage
    req_cov = coverage.get('required_fields_coverage', {'total': 0, 'covered': 0, 'missing': []})
    if req_cov['total'] > 0:
        st.markdown(f"**Required Fields Coverage:** {req_cov['covered']}/{req_cov['total']} covered")
        if req_cov['missing']:
            st.info(f"Missing Required: `{', '.join(req_cov['missing'])}`")
        st.progress(req_cov['covered'] / req_cov['total'])
    else:
        st.info("No required fields defined in schema or data is empty.")

    # Enum Coverage (simplified)
    enum_cov = coverage.get('enum_coverage', {})
    if enum_cov:
        st.markdown("**Enum Value Coverage:**")
        for field, details in enum_cov.items():
            st.markdown(f"- `{field}`: {details.get('covered',0)}/{details.get('total',0)} values covered")
            if details.get('missing'):
                st.info(f"  Missing: `{', '.join(map(str, details['missing']))}`")
    else:
        st.info("No enum fields or enum coverage data.")

    # Min/Max Coverage (simplified)
    min_max_cov = coverage.get('min_max_coverage', {})
    if min_max_cov:
        st.markdown("**Min/Max Boundary Coverage:**")
        for field, details in min_max_cov.items():
            status_min = "✅" if details.get('min_boundary_tested') else "❌"
            status_max = "✅" if details.get('max_boundary_tested') else "❌"
            st.markdown(f"- `{field}`: Min Tested {status_min}, Max Tested {status_max}")
            if not details.get('min_boundary_tested') and details.get('min_constraint') is not None:
                st.info(f"  Smallest value found: {details.get('min_data_value', 'N/A')} (expected near {details.get('min_constraint')})")
            if not details.get('max_boundary_tested') and details.get('max_constraint') is not None:
                st.info(f"  Largest value found: {details.get('max_data_value', 'N/A')} (expected near {details.get('max_constraint')})")
    else:
        st.info("No numeric fields with min/max constraints or coverage data.")


    # AI Suggestions
    st.subheader("💡 AI Suggestions")
    if st.session_state['ai_suggestions_test_cases'] or st.session_state['ai_suggestions_schema']:
        if st.session_state['ai_suggestions_test_cases']:
            st.markdown("#### AI-Suggested Test Case Improvements")
            for i, suggestion in enumerate(st.session_state['ai_suggestions_test_cases']):
                st.markdown(f"**{i+1}. Field `{suggestion.get('field', 'N/A')}` ({suggestion.get('issue_type', 'N/A')}):**")
                st.markdown(f"- Recommended Value: `{json.dumps(suggestion.get('recommended_value'))}`")
                st.markdown(f"- Explanation: {suggestion.get('explanation', 'N/A')}")
                st.markdown("---")
        
        if st.session_state['ai_suggestions_schema']:
            st.markdown("#### AI-Suggested Schema Improvements")
            for i, suggestion in enumerate(st.session_state['ai_suggestions_schema']):
                st.markdown(f"**{i+1}. Path `{suggestion.get('schema_path', 'N/A')}` ({suggestion.get('improvement_type', 'N/A')}):**")
                st.code(suggestion.get('suggested_snippet', 'N/A'), language='json')
                st.markdown(f"- Explanation: {suggestion.get('explanation', 'N/A')}")
                st.markdown("---")
    else:
        st.info("No AI suggestions generated (either disabled or no issues found).")

log_message('info', "App: Finished Section 2 rendering.")


# --- SECTION 3: AI-Powered Test Case Generation ---
st.header("3. AI-Powered Test Case Generation")
st.markdown("Generate new synthetic test data using AI, optionally focusing on specific criteria.")
log_message('info', "App: Section 3 header and markdown rendered.")

if st.session_state['enable_ai_test_case_generation']:
    if st.session_state['contract_schema']:
        st.session_state['user_test_case_prompt'] = st.text_area(
            "Describe the type of test cases you want to generate (e.g., '5 edge cases for numeric fields', '10 cases covering all enum values', 'data with missing required fields'):",
            value=st.session_state['user_test_case_prompt'],
            height=100,
            key="test_case_generation_prompt"
        )
        num_cases_to_generate = st.slider("Number of test cases to generate:", 1, 50, 5, key="num_cases_slider")

        col_gen_1, col_gen_2 = st.columns(2)
        with col_gen_1:
            generate_button = st.button("✨ Generate Test Cases", key="generate_test_cases_button")
        with col_gen_2:
            # Option to reverse engineer schema if no contract is uploaded
            if not st.session_state['contract_schema'] and not st.session_state['synthetic_data_df'].empty:
                if st.button("🧠 Reverse-Engineer Schema from Uploaded Data", key="reverse_engineer_schema_button"):
                    with st.spinner("Reverse-engineering schema from data..."):
                        reverse_schema_result = test_case_generator.reverse_engineer_schema_from_data(st.session_state['synthetic_data_df'])
                        if reverse_schema_result.get('error'):
                            st.error(f"Schema Reverse-Engineering Error: {reverse_schema_result['error']}")
                            log_message('error', f"App: Schema reverse-engineering failed: {reverse_schema_result['error']}")
                        else:
                            st.session_state['ai_patched_schema'] = reverse_schema_result['schema'] # Use this to display
                            st.success("Schema reverse-engineered successfully! See 'AI-Patched Schema Suggestion' in Section 4.")
                            log_message('info', "App: Schema reverse-engineered successfully.")
            else:
                st.info("Upload data and no schema to enable schema reverse-engineering.")


        if generate_button:
            if not st.session_state['gemini_api_key_loaded']:
                st.error("Gemini API key not loaded. Please provide it in the sidebar.")
            elif not st.session_state['contract_schema']:
                st.error("Please upload a schema contract first to generate test cases.")
            else:
                st.session_state['ai_test_case_generation_error'] = None
                with st.spinner(f"Generating {num_cases_to_generate} test cases..."):
                    # Pass relevant errors/warnings to focus generation
                    focus_issues = st.session_state['validation_report'].get('errors', []) + st.session_state['validation_report'].get('warnings', []) if st.session_state['validation_report'] else []
                    
                    generated_cases_result = test_case_generator.generate_synthetic_test_cases(
                        schema=st.session_state['contract_schema'],
                        num_cases=num_cases_to_generate,
                        focus_on_issues=focus_issues,
                        specific_instructions=st.session_state['user_test_case_prompt']
                    )
                    if generated_cases_result.get('error'):
                        st.session_state['ai_test_case_generation_error'] = generated_cases_result['error']
                        st.error(f"AI Test Case Generation Error: {generated_cases_result['error']}")
                        log_message('error', f"App: AI test case generation failed: {generated_cases_result['error']}")
                    else:
                        st.session_state['ai_generated_test_cases_df'] = pd.DataFrame(generated_cases_result['test_cases'])
                        st.success(f"Successfully generated {len(st.session_state['ai_generated_test_cases_df'])} test cases!")
                        log_message('info', f"App: Successfully generated {len(st.session_state['ai_generated_test_cases_df'])} test cases.")
                st.rerun()
        
        if st.session_state['ai_test_case_generation_error']:
            st.error(st.session_state['ai_test_case_generation_error'])

        if not st.session_state['ai_generated_test_cases_df'].empty:
            st.subheader("Generated Test Cases Preview")
            st.dataframe(st.session_state['ai_generated_test_cases_df'], use_container_width=True)
    else:
        st.info("Upload a schema contract to enable AI test case generation.")
else:
    st.info("AI Test Data Generation is disabled in the sidebar.")

log_message('info', "App: Finished Section 3 rendering.")


# --- SECTION 4: Export Reports ---
st.header("4. Export Reports & Test Data")
st.markdown("Download comprehensive validation reports and generated test data.")
log_message('info', "App: Section 4 header and markdown rendered.")

if st.session_state['validation_report'] or not st.session_state['ai_generated_test_cases_df'].empty:
    # Download Markdown Report
    if st.session_state['validation_report'] or st.session_state['ai_suggestions_test_cases'] or st.session_state['ai_suggestions_schema'] or st.session_state['ai_patched_schema']:
        markdown_report_content = generate_markdown_report(
            contract_schema=st.session_state['contract_schema'],
            synthetic_data_info=st.session_state['synthetic_data_info'],
            validation_report=st.session_state['validation_report'],
            ai_suggestions_test_cases=st.session_state['ai_suggestions_test_cases'],
            ai_suggestions_schema=st.session_state['ai_suggestions_schema'],
            ai_patched_schema=st.session_state['ai_patched_schema'],
            user_prompt_for_test_cases=st.session_state['user_test_case_prompt']
        )
        st.download_button(
            label="📄 Download Full Validation Report (Markdown)",
            data=markdown_report_content,
            file_name=f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            key="download_md_report"
        )
    else:
        st.info("Run validation or generate AI data to create a full report.")

    # Download Failed Cases CSV
    if st.session_state['validation_report'] and st.session_state['validation_report'].get('errors'):
        failed_cases_csv = export_failed_cases_csv(
            st.session_state['synthetic_data_df'],
            st.session_state['validation_report']['errors']
        )
        if failed_cases_csv:
            st.download_button(
                label="📥 Download Failed Test Cases (CSV)",
                data=failed_cases_csv,
                file_name=f"failed_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_failed_csv"
            )
        else:
            st.info("No failed cases to export to CSV.")
    else:
        st.info("No validation errors found, so no failed cases CSV to download.")

    # Download AI Generated Test Cases CSV
    if not st.session_state['ai_generated_test_cases_df'].empty:
        ai_generated_csv = export_ai_generated_test_cases_csv(st.session_state['ai_generated_test_cases_df'].to_dict(orient='records'))
        if ai_generated_csv:
            st.download_button(
                label="📥 Download AI Generated Test Cases (CSV)",
                data=ai_generated_csv,
                file_name=f"ai_generated_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_ai_generated_csv"
            )
    else:
        st.info("No AI-generated test cases to download.")

else:
    st.info("Perform validation or generate test cases to enable report exports.")

log_message('info', "App: Finished Section 4 rendering.")


# --- Reset Button (in sidebar) ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Application", key="reset_app_button"):
    st.session_state.clear()
    st.rerun()
log_message('info', "App: End of Streamlit application script.")
