# synthetic-validator/utils/logging_utils.py

import logging
import os

# --- Logging Configuration ---
# Configure logging to show information and errors in the terminal
# where Streamlit is run.
# Set a basic configuration that can be imported and used by other modules.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_message(level: str, message: str, **kwargs):
    """
    Custom logging function that directs messages to the standard Python logger.
    This function is intended for internal application logging (to console/terminal).
    For user-facing messages in the Streamlit UI, use `st.info`, `st.warning`, `st.error` directly in `app.py`.

    Args:
        level (str): The log level (e.g., 'info', 'warning', 'error', 'debug').
        message (str): The log message.
        **kwargs: Additional keyword arguments to pass to the logger (e.g., exc_info=True for exceptions).
    """
    if level.lower() == 'info':
        logging.info(message, **kwargs)
    elif level.lower() == 'warning':
        logging.warning(message, **kwargs)
    elif level.lower() == 'error':
        logging.error(message, **kwargs)
    elif level.lower() == 'debug':
        logging.debug(message, **kwargs)
    else:
        logging.info(f"Unknown log level '{level}': {message}", **kwargs)

# You can add more specific loggers here if needed, e.g., for file logging.
# For now, basic console logging is sufficient for a Streamlit MVP.