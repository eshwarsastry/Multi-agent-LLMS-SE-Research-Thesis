import json
import os
from dotenv import load_dotenv

def load_config(config_path):
    # Load environment variables from .env file
    load_dotenv()

    print("Trying to open config at:", config_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get the default configuration from environment variable
    default_config = os.getenv('DEFAULT_LLM_CONFIG')
    
    # Update configuration with environment variables
    llm_config = config['llm_configurations'][default_config]
    
    # Update API keys and URLs from environment variables
    for config_item in llm_config['config_list']:
        if default_config == 'codellama':
            config_item['base_url'] = os.getenv('OLLAMA_BASE_URL')
        elif default_config == 'qwen_25_coder_35b_instruct':
            config_item['api_key'] = os.getenv('QWEN_API_KEY')
            config_item['base_url'] = os.getenv('QWEN_BASE_URL')

    # Set up SSL certificate bundle
    requests_ca_bundle = os.getenv('REQUESTS_CA_BUNDLE')
    if requests_ca_bundle:
        os.environ['REQUESTS_CA_BUNDLE'] = requests_ca_bundle 
        
    return llm_config['config_list']
