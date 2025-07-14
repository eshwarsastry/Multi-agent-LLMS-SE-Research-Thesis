import os
from datetime import datetime

def extract_value(key, messages):
    """Helper function to extract values from messages"""
    for msg in reversed(messages):
        if key in msg["content"]:
            return msg["content"].split(key)[1].strip()
    return ""

def save_requirements_to_file(requirements_content, filename="requirements.md"):
    """Save requirements to a markdown file"""
    # Create output directory if it does not exist
    output_dir = "system output/re docs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"{filename}_{timestamp}.md")
    
    # Write requirements to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(requirements_content)
    
    return filepath 