import json
import os
from dotenv import load_dotenv

def load_config(config_path):
    # Load environment variables from .env file
    load_dotenv()

    print("Trying to open config at:", config_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Set up SSL certificate bundle
    requests_ca_bundle = os.getenv('REQUESTS_CA_BUNDLE')
    if requests_ca_bundle:
        os.environ['REQUESTS_CA_BUNDLE'] = requests_ca_bundle 
    
    # Return all LLM configurations as a dict
    return config['llm_configurations']
