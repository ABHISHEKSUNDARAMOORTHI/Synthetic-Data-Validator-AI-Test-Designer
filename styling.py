# synthetic-validator/styling.py

import streamlit as st

def inject_custom_css():
    """
    Injects custom CSS into the Streamlit app for a consistent dark theme
    and enhanced UI elements, tailored for the Synthetic Data Validator.
    """
    st.markdown("""
    <style>
        /* Overall App Container */
        .stApp {
            background-color: #0e1117; /* Dark background */
            color: #ffffff; /* White text */
            font-family: 'Inter', sans-serif; /* Use Inter font */
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff;
            font-family: 'Inter', sans-serif;
            font-weight: 600; /* Semi-bold */
        }

        /* Sidebar Styling */
        .stSidebar {
            background-color: #1a1e24; /* Slightly lighter dark for sidebar */
            color: #ffffff;
            border-radius: 0.75rem; /* Rounded corners for sidebar */
            padding: 1rem;
            margin: 0.5rem; /* Margin around the sidebar */
        }
        .stSidebar .stButton > button {
            color: #ffffff;
            border-color: #2563eb;
            border-radius: 0.5rem;
        }

        /* Main Content Area - rounded corners for individual sections */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
            border-radius: 0.75rem; /* Rounded corners for main content blocks */
            background-color: #1c1f26; /* Darker grey for content areas */
            margin-bottom: 1.5rem; /* Increased space between sections */
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); /* More prominent shadow */
        }

        /* Buttons */
        .stButton > button {
            background-color: #2563eb; /* Primary blue */
            color: white;
            border-radius: 0.5rem;
            padding: 0.75rem 1.25rem;
            border: none;
            transition: background-color 0.2s, transform 0.1s;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); /* Subtle shadow */
        }
        .stButton > button:hover {
            background-color: #1a56cc;
            transform: translateY(-2px); /* Slight lift on hover */
        }
        .stButton > button:active {
            transform: translateY(0);
        }

        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #2a2e35; /* Slightly lighter for expander headers */
            color: #ffffff;
            border-radius: 0.5rem;
            border: 1px solid #33363e;
            padding: 0.75rem 1.25rem;
            margin-bottom: 0.5rem;
            transition: background-color 0.2s;
        }
        .streamlit-expanderHeader:hover {
            background-color: #333842;
        }
        .streamlit-expanderContent {
            background-color: #1c1f26; /* Same as main content for consistency */
            border-radius: 0.5rem;
            border: 1px solid #33363e;
            border-top: none; /* No top border to blend with header */
            padding: 1rem;
            margin-bottom: 1rem;
        }

        /* Input Widgets (text input, file uploader, selectbox, slider) */
        .stTextInput > div > div > input,
        .stFileUploader > div > button,
        .stSelectbox > div > div,
        .stSlider .st-cl, /* Slider track */
        .stTextArea > div > div { /* Text Area */
            background-color: #1c1f26;
            color: #ffffff;
            border: 1px solid #33363e;
            border-radius: 0.5rem;
        }
        .stTextInput > div > div > input:focus,
        .stFileUploader > div > button:focus,
        .stSelectbox > div > div:focus-within,
        .stTextArea > div > div:focus-within {
            border-color: #2563eb;
            box-shadow: 0 0 0 0.1rem #2563eb;
        }
        .stSlider .st-ce { /* Slider thumb */
            background-color: #2563eb;
            border: 2px solid #ffffff;
        }

        /* Info, Warning, Error boxes */
        .stAlert {
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        /* Code Blocks */
        .stCode {
            background-color: #2a2e35; /* Darker background for code */
            border-radius: 0.5rem;
            padding: 1rem;
            font-family: 'Fira Code', 'Cascadia Code', monospace; /* Monospace font for code */
            font-size: 0.9rem;
            color: #e0e0e0; /* Light grey text for code */
            overflow-x: auto; /* Allow horizontal scrolling for long lines */
            margin-top: 1rem;
            margin-bottom: 1rem;
        }

        /* Dataframe Styling */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden; /* Ensures rounded corners apply to content */
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        /* Make dataframe headers and rows readable in dark mode */
        .stDataFrame table {
            color: #ffffff;
        }
        .stDataFrame th {
            background-color: #2a2e35 !important; /* Darker header background */
            color: #ffffff !important;
        }
        .stDataFrame tr:nth-child(even) {
            background-color: #1c1f26; /* Even row background */
        }
        .stDataFrame tr:nth-child(odd) {
            background-color: #1a1e24; /* Odd row background */
        }

        /* Plotly/Altair chart containers */
        .stPlotlyChart, .stAltairChart {
            border-radius: 0.5rem;
            overflow: hidden;
            background-color: #1c1f26; /* Match background for charts */
            padding: 1rem;
            margin-top: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        /* Custom AI Explanation/Feedback Box */
        .ai-feedback-box {
            background-color: #2a2e35; /* Slightly lighter than content blocks */
            border-left: 5px solid #9333ea; /* Purple accent */
            padding: 1rem 1.5rem;
            margin-top: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            color: #ffffff;
            line-height: 1.6;
        }
        .ai-feedback-box p {
            margin-bottom: 0.5rem;
        }
        .ai-feedback-box strong {
            color: #9333ea; /* Highlight strong text in purple */
        }

        /* Progress Bar Customization */
        .stProgress > div > div > div > div {
            background-color: #2563eb; /* Blue progress bar */
        }
        .stProgress > div > div > div {
            background-color: #33363e; /* Darker background for progress track */
        }

        /* Specific styles for badges/icons if needed, e.g., for validation status */
        .status-badge {
            display: inline-block;
            padding: 0.25em 0.6em;
            font-size: 0.85em;
            font-weight: bold;
            line-height: 1;
            color: #fff;
            text-align: center;
            white-space: nowrap;
            vertical-align: middle;
            border-radius: 0.25rem;
            margin-left: 0.5rem;
        }
        .status-badge.pass { background-color: #28a745; } /* Green */
        .status-badge.warning { background-color: #ffc107; color: #333; } /* Yellow */
        .status-badge.fail { background-color: #dc3545; } /* Red */

    </style>
    """, unsafe_allow_html=True)