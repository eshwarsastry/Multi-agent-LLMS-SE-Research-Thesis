import json
import os
import re
from datetime import datetime

def extract_value(key, messages):
    """Helper function to extract values from messages"""
    for msg in reversed(messages):
        if key in msg["content"]:
            return msg["content"].split(key)[1].strip()
    return ""

def save_output_to_file(output_content, filename, output_dir):
    """Save the agent output contents of the agent to a markdown file in the specified directory"""
    # Create output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"{filename}_{timestamp}.md")
    
    # Write the agent output contents to the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    return filepath 

def extract_relevant_outputs(messages, agent_patterns):
    outputs = {}
    for agent, pattern in agent_patterns.items():
        for msg in reversed(messages):
            if msg.get("name") == agent and all(p in msg["content"] for p in pattern):
                outputs[agent] = msg["content"]
                break
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

def get_last_python_code_block(chat_history):
    """
    Finds and returns the content of the last Python code block
    in a list of chat messages using a regex match.
    """
    code_pattern = r'```(python|py|python3)\n(.*?)```'
    
    last_code = None
    for message in chat_history:
        content = message.get('content', '')
        
        # Find all matches in the current message
        code_blocks = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # If any code blocks were found, update the 'last_code'
        if code_blocks:
            # The regex captures two groups: the tag and the code.
            # We want the code, which is the second group.
            last_code = code_blocks[-1][1]
            
    return last_code