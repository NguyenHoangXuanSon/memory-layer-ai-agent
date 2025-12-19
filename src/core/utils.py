import re
import json
import logging

def safe_json_loads(generated_text: str):

    """
    Convert output text from Gemini into safe JSON.
    """

    if not generated_text:
        logging.warning("The input from Gemini is empty.")
        return None
    
    cleaned_text = re.sub(r"^```[a-zA-Z]*\n?", "", generated_text.strip())
    cleaned_text = re.sub(r"```$", "", cleaned_text.strip())

    try:
        cleaned_text_json = json.loads(cleaned_text)
        return cleaned_text_json
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\n Content after cleaning:\n{cleaned_text}")