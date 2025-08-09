import os
import json
import re
# Load the configuration loader service for the agents.
from services.config_loader import load_config

# Load the prompts for the agents.
from prompts.translator_agent_prompts import translator_prompt_1
from prompts.user_proxy_agent_prompts import user_proxy_prompt1

# Load the services for the agents.
from services.agent_factory import AgentFactory
from services.agent_helpers import get_last_python_code_block, read_json_file

# Load the configuration file path of the agents.
base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "llm_config.json")

# Load all LLM configurations for the agents.
llm_configs = load_config(config_path)

# Create an agent factory with mistral as default, but Qwen for Code_Translator
agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.5)

# Set temperature for Qwen model (optional)
agent_factory.set_model_temperature("qwen_25_coder_35b_instruct", 0.1)  # Lower temperature for more deterministic output

# Create the agents using the agent factory.

# Code Translator (Qwen)
# Override temperature for Qwen
if "qwen_25_coder_35b_instruct" in llm_configs:
    llm_configs["qwen_25_coder_35b_instruct"]["temperature"] = 0.0  # Set to desired temperature

code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_prompt_1,
    tools=[],
    llm_model="qwen_25_coder_35b_instruct"
)

# User Proxy Agent
user_proxy = agent_factory.create_user_proxy(
    name="User_Proxy",
    system_messages=[user_proxy_prompt1],
)

output_file_path = 'D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/generated_python_code.json'
input_cpp_codes = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/inputs/input_program.json')

translations = {}
for key, cpp_code in input_cpp_codes.items():
    print(f"Translating C++ code for key: {key}")
    chat_result = user_proxy.initiate_chat(
    code_translator,
    message="Translate the following C++ code to Python:\n" + cpp_code,
    max_turns=1)
    python_code = get_last_python_code_block(chat_result.chat_history)
    
    #If python code is found, then store it output> generated_python_code.json along with the key
    if python_code:
        translations[key] = python_code
    else:
        print(f"No Python code found for key: {key}")

with open(output_file_path, 'w', encoding='utf-8') as f:
    json.dump(translations, f, ensure_ascii=False, indent=2)