import os
import json
from pathlib import Path

# Load the prompts for the agents.
from ..prompts.translator_agent_prompts import translator_prompt_1
from ..prompts.user_proxy_agent_prompts import user_proxy_prompt1

# Load the services for the agents.
from ..services.agent_factory import AgentFactory
from ..services.agent_helpers import extract_relevant_outputs, read_json_file, save_output_to_json_file 
from ..services.result_evaluation import evaluate_codebleu_for_pairs, print_codebleu_results
from ..services.config_loader import load_config

# Static values and variables
agent_patterns = {
        "Code_Translator": [r'```(python|py|python3)\n(.*?)```']
    }
translations = {}
output_file_path = 'D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/single_agent_results/generated_python_code.json'

# Load the configuration file path of the agents.
current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
config_path = os.path.join(base_dir, "llm_config.json")

# Load all LLM configurations for the agents.
llm_configs = load_config(config_path)

# Create an agent factory with mistral as default, but Qwen for Code_Translator
agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.2)

# Set temperature for Qwen model
agent_factory.set_model_temperature("qwen_25_coder_35b_instruct", 0.1)  # Lower temperature for more deterministic output

# Create the agents using the agent factory.

# Code Translator (Qwen)
code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_prompt_1,
    llm_model="qwen_25_coder_35b_instruct"
)

# User Proxy Agent
user_proxy = agent_factory.create_user_proxy(
    name="User_Proxy",
    system_messages=[user_proxy_prompt1],
)

input_cpp_codes = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/inputs/input_program.json')


for key, cpp_code in list(input_cpp_codes.items())[:10]:
    print(f"Translating C++ code for key: {key}")
    chat_result = user_proxy.initiate_chat(
    code_translator,
    message="Translate the following C++ code to Python:\n" + cpp_code,
    max_turns=1)
    output = extract_relevant_outputs(chat_result.chat_history, agent_patterns)

    for agent in agent_patterns:
        if output.get(agent):
            if agent == "Code_Translator":
                # Store only the first code block as a string, or "" if not found
                translations[key] = output[agent][0] if output[agent] else ""
        else:
            print(f"No output found for agent: {agent} and key: {key}")

    save_output_to_json_file(output_file_path, translations)

#Evaluating code Bleu score
ground_truth = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/inputs/ground_truth.json')
generated_code = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/single_agent_results/generated_python_code.json')

results = evaluate_codebleu_for_pairs(ground_truth, generated_code, lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)

print_codebleu_results(results)