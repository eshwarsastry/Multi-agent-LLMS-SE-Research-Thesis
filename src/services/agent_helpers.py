import json
import os
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
    Load the value for a given key from a JSON file. If no key is provided, return the whole content.
    """
    with open(file_path, 'r') as file:
        file_content = file.read()

    return file_content

