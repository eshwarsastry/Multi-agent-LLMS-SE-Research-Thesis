import json
import re

def extract_relevant_outputs(chat_history, agent_patterns):
    """
    Finds and returns the content of the agent messages
    that match the specified patterns. Returns only the most recent match.
    """
    outputs = {}
    for agent, regex_patterns in agent_patterns.items():
        # Ensure regex_patterns is a list
        if not isinstance(regex_patterns, list):
            regex_patterns = [regex_patterns]
        matches = []
        for message in chat_history:
            # Handle None messages
            if message is None:
                continue
            # Support both dict and str, with None check
            content = message.get('content', '') if isinstance(message, dict) and 'content' in message and message.get('content') is not None else str(message) if message is not None else ''
            for pattern in regex_patterns:
                found = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                # Special handling for Code_Translator: extract only the code (second group)
                if agent == "Code_Translator" and found and isinstance(found[0], tuple):
                    matches.extend([code for (_, code) in found])
                else:
                    matches.extend(found)
        
        # Return only the last match if any matches were found, otherwise empty list
        outputs[agent] = [matches[-1]] if matches else []
    return outputs

def save_output_to_json_file(output_file_path, output_content):
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_content, f, ensure_ascii=False, indent=2)

def read_json_file(file_path):
	"""
	Read the contents of a JSON file.
	"""
	with open(file_path, 'r', encoding='utf-8') as file:
		file_json_content = json.load(file)

	return file_json_content