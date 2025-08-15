import json
import re
from datetime import datetime

def extract_value(key, messages):
    """Helper function to extract values from messages using regex matching"""
    pattern = re.compile(rf"{key}\s*:\s*(.*)", re.IGNORECASE)
    for msg in reversed(messages):
        # Support both dict and str
        content = msg["content"] if isinstance(msg, dict) and "content" in msg else str(msg)
        found = pattern.findall(content)
        if found:
            return found[0].strip()
    return ""

def save_output_to_json_file(output_file_path, output_content):
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_content, f, ensure_ascii=False, indent=2)

def extract_relevant_outputs(chat_history, agent_patterns):
    """
    Finds and returns the content of the agent messages
    that match the specified patterns
    """
    outputs = {}
    for agent, regex_patterns in agent_patterns.items():
        # Ensure regex_patterns is a list
        if not isinstance(regex_patterns, list):
            regex_patterns = [regex_patterns]
        matches = []
        for message in chat_history:
            # Support both dict and str
            content = message.get('content', '') if isinstance(message, dict) and 'content' in message else str(message)
            for pattern in regex_patterns:
                found = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                # Special handling for Code_Translator: extract only the code (second group)
                if agent == "Code_Translator" and found and isinstance(found[0], tuple):
                    matches.extend([code for (_, code) in found])
                else:
                    matches.extend(found)
        outputs[agent] = matches
    return outputs
    
def load_input_from_file(file_path, key=None):
    """
    Read the contents of a file.
    """
    with open(file_path, 'r') as file:
        file_content = file.read()

    return file_content

def read_json_file(file_path):
	"""
	Read the contents of a JSON file.
	"""
	with open(file_path, 'r', encoding='utf-8') as file:
		file_json_content = json.load(file)

	return file_json_content