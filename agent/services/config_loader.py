import json

def load_config(config_path="./llm_config.json"):
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['llm_configurations']["codellama"]["config_list"]
