import os
import json
from pathlib import Path
# Load the configuration loader service for the agents.
from ..services.agent_workflow import WorkflowController
from ..services.config_loader import load_config

# Load the prompts for the agents.
from ..prompts.re_agent_prompts import re_prompt_1
from ..prompts.translator_agent_prompts import translator_prompt_2
from ..prompts.user_proxy_agent_prompts import user_proxy_prompt1

# Load the services for the agents.
from ..services.agent_factory import AgentFactory
from ..services.agent_helpers import extract_relevant_outputs, read_json_file, save_output_to_json_file
from ..services.agent_speaker_selector import SpeakerSelector
from ..services.result_evaluation import evaluate_codebleu_for_pairs, print_codebleu_results

# Static values and variables
agent_patterns = {
        "Requirement_Engineer": [r"Title:\s*.*"],
        "Code_Translator": [r'```(python|py|python3)\n(.*?)```']
    }

translations = {}
requirements = {}
    
PHASE_ORDER = ["REQUIREMENTS", "TRANSLATION"]

output_file_path = 'D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/double_agent_results/generated_python_code.json'
requirements_file_path = 'D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/double_agent_results/generated_requirements.json'

# Load the configuration file path of the agents.
current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
config_path = os.path.join(base_dir, "llm_config.json")

# Load all LLM configurations for the agents.
llm_configs = load_config(config_path)

# Create an agent factory with mistral as default, but Qwen for Code_Translator
agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.5)
# Set temperature for Qwen model
agent_factory.set_model_temperature("qwen_25_coder_35b_instruct", 0.1)  # Lower temperature for more deterministic output

# Create the agents using the agent factory.
#Requirement Engineer
requirement_engineer = agent_factory.create_assistant(
    name="Requirement_Engineer",
    system_message=re_prompt_1,
    tools=[],
    llm_model="qwen_25_coder_35b_instruct"
)

# Code Translator (Qwen)
code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_prompt_2,
    tools=[],
    llm_model="qwen_25_coder_35b_instruct"
)

# User Proxy Agent
user_proxy = agent_factory.create_user_proxy(
    name="User_Proxy",
    system_messages=[user_proxy_prompt1],
)

# Define phases for the workflownext
# Define workflow phases with retry conditions and optional parallel agents
PHASES = {
    "REQUIREMENTS": {
        "agents": [requirement_engineer],
        "retry_on": ["missing requirements"]
    },
    "TRANSLATION": {
        "agents": [code_translator],
        "retry_on": []
    }
}

input_cpp_codes = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/inputs/input_program.json')

for key, cpp_code in list(input_cpp_codes.items())[:10]:
    print(f"Translating C++ code for key: {key}")

    workflow_controller = WorkflowController(PHASES, PHASE_ORDER)
    speaker_selector = SpeakerSelector(workflow_controller, requirement_engineer)
    
    groupchat = agent_factory.create_groupchat(
        agents=[requirement_engineer, code_translator],
        speaker_selector=speaker_selector.select_speaker,
        max_round=4
    )
    
    group_chat_manager = agent_factory.create_group_manager(
        groupchat=groupchat
    )

    user_proxy.initiate_chat(
        group_chat_manager,
        message="Translate the following C++ code to Python:\n" + cpp_code)
    output = extract_relevant_outputs(groupchat.messages, agent_patterns)

    # Store outputs for all agents in agent_patterns
    for agent in agent_patterns:
        if output.get(agent):
            if agent == "Code_Translator":
                # Store only the first code block as a string, or "" if not found
                translations[key] = output[agent][0] if output[agent] else ""
            elif agent == "Requirement_Engineer":
                requirements[key] = output[agent][0] if output[agent] else ""
        else:
            print(f"No output found for agent: {agent} and key: {key}")

    save_output_to_json_file(output_file_path, translations)
    save_output_to_json_file(requirements_file_path, requirements)


#Evaluating code Bleu score
ground_truth = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/inputs/ground_truth.json')
generated_code = read_json_file('D:/TUK/Master_Thesis/Multi-agent-LLMS-SE-Research-Thesis/src/outputs/double_agent_results/generated_python_code.json')

results = evaluate_codebleu_for_pairs(ground_truth, generated_code, lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)

print_codebleu_results(results)
