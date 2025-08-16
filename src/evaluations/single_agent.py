import os
from pathlib import Path
import time

# Load the prompts for the agents.
from ..prompts.single_agent_prompts import translator_message, user_proxy_message, user_proxy_prompt

# Load the services for the agents.
from ..services.agent_factory import AgentFactory
from ..services.agent_helpers import extract_relevant_outputs, read_json_file, save_output_to_json_file 
from ..services.config_loader import load_config

# Output paths (separate folder for custom sequential flow)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs' / 'single_agent_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CODE_OUT = OUTPUT_DIR / 'generated_python_code.json'
TIME_LOG = OUTPUT_DIR / 'time_log.json'
INPUT_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'input_program.json'

# Static values and variables
agent_patterns = {
        "Code_Translator": [r'```(python|py|python3)\n(.*?)```']
    }
translations = {}
time_log = {}

# Load the configuration file path of the agents.
current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
config_path = os.path.join(base_dir, "llm_config.json")

# Load all LLM configurations for the agents.
llm_configs = load_config(config_path)

# Create an agent factory with mistral as default, but Qwen for Code_Translator
agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.2)

# Set temperature for Qwen model
agent_factory.set_model_temperature("qwen_coder", 0.1)  # Lower temperature for more deterministic output

# Create the agents using the agent factory.

# Code Translator (Qwen)
code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_message,
    llm_model="qwen_coder"
)

# User Proxy Agent
user_proxy = agent_factory.create_user_proxy(
    name="User_Proxy",
    system_messages=[user_proxy_message],
)

input_cpp_codes = read_json_file(str(INPUT_PATH))

for key, cpp_code in list(input_cpp_codes.items()):
    print(f"Translating C++ code for key: {key}")
    start_time = time.time()
    chat_result = user_proxy.initiate_chat(
    code_translator,
    message=user_proxy_prompt + cpp_code,
    max_turns=1)
    output = extract_relevant_outputs(chat_result.chat_history, agent_patterns)
    end_time = time.time()
    for agent in agent_patterns:
        if output.get(agent):
            if agent == "Code_Translator":
                # Store only the first code block as a string, or "" if not found
                translations[key] = output[agent][0] if output[agent] else ""
        else:
            print(f"No output found for agent: {agent} and key: {key}")
    
    save_output_to_json_file(str(CODE_OUT), translations)
    # Log the time taken for this translation
    time_taken = end_time - start_time
    time_log[key] = time_taken
    save_output_to_json_file(str(TIME_LOG), time_log)
