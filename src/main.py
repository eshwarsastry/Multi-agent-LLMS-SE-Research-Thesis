import os
from typing import Dict
from typing_extensions import Annotated
 
# Load the configuration loader service for the agents.
from services.config_loader import load_config

# Load the prompts for the agents.
from prompts.re_agent_prompts import re_prompt_1
from prompts.translator_agent_prompts import translator_prompt_1
from prompts.validator_agent_prompts import validator_prompt_1
from prompts.tester_agent_prompts import code_tester_prompt_1
from prompts.critic_agent_prompts import critic_prompt_1
from prompts.user_proxy_agent_prompts import user_proxy_prompt1, user_proxy_message

# Load the services for the agents.
from services.agent_workflow import WorkflowController
from services.agent_speaker_selector import SpeakerSelector
from services.agent_factory import AgentFactory
from services.agent_helpers import extract_relevant_outputs, save_output_to_file, load_input_from_file
from services.output_testing import run_and_compare_tests

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
# Requirement Engineer
requirement_engineer = agent_factory.create_assistant(
    name="Requirement_Engineer",
    system_message=re_prompt_1,
    tools=[]
)

# Code Translator (Qwen)
# Override temperature for Qwen
if "qwen_25_coder_35b_instruct" in llm_configs:
    llm_configs["qwen_25_coder_35b_instruct"]["temperature"] = 0.1  # Set to desired temperature

code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_prompt_1,
    tools=[],
    llm_model="qwen_25_coder_35b_instruct"
)

# Code Validator (Mistral)
code_validator = agent_factory.create_assistant(
    name="Code_Validator",
    system_message=validator_prompt_1,
    tools=[]
)

# Code Tester (Mistral)
code_tester = agent_factory.create_assistant(
    name="Code_Tester",
    system_message=code_tester_prompt_1,
    tools=[]
)

# Critic (Mistral)
critic = agent_factory.create_assistant(
    name="Critic",
    system_message=critic_prompt_1,
    tools=[]
)

# User Proxy Agent
user_proxy = agent_factory.create_user_proxy(
    name="User_Proxy",
    system_messages=[user_proxy_prompt1],
)

# Register the tool signature with the assistant agent.
print(" Registering functions with Code_Tester agent...")
@user_proxy.register_for_execution()
@code_tester.register_for_llm(description="Run given test cases on both codes and return pass/fail summary")
def execute_and_compare_tests(
    legacy_code: Annotated[str, "C++ program string provided"],
    translated_code: Annotated[str, "Python program string translated"],
    cpp_tests: Annotated[str, "C++ test methods"],
    py_tests: Annotated[str, "Python test methods"],
) -> Dict:
    """ Execute test cases on both legacy and translated code, returning pass/fail summary.
    """ 
    compute_result = run_and_compare_tests(
        legacy_code=legacy_code,
        translated_code=translated_code,
        cpp_tests=cpp_tests,
        py_tests=py_tests
    )
    return compute_result
# Define phases for the workflow
# Define workflow phases with retry conditions and optional parallel agents
PHASES = {
    "REQUIREMENTS": {
        "agents": [requirement_engineer],
        "retry_on": ["missing requirements"]
    },
    "TRANSLATION": {
        "agents": [code_translator],
        "retry_on": ["syntax error", "test fail", "low score"]
    },
    "VALIDATION": {
        "agents": [code_validator],
        "retry_on": ["syntax error"]
    },
    "TESTING": {
        # Example of parallel phase with tester and critic
        "agents": [code_tester, critic],
        "retry_on": ["output mismatch"]
    },
    "REVIEW": {
        "agents": [critic],
        "retry_on": ["low score"]
    },
    "COMPLETE": {
        "agents": [],
        "retry_on": []
    }
}

# Explicit phase order
PHASE_ORDER = ["REQUIREMENTS", "TRANSLATION", "VALIDATION", "TESTING", "REVIEW", "COMPLETE"]

# Create workflow controller
workflow_controller = WorkflowController(PHASES, PHASE_ORDER)

# Create speaker selector
speaker_selector = SpeakerSelector(workflow_controller, requirement_engineer)

# Group Chat for all agents except User Proxy (which is the initiator)
groupchat = agent_factory.create_groupchat(
    agents=[requirement_engineer, code_translator, code_validator, code_tester, critic],
    speaker_selector= speaker_selector.select_speaker,
    max_round=20
)

# Create group chat manager
group_chat_manager = agent_factory.create_group_manager(
    groupchat=groupchat
)

base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_dir)
inputs_dir = os.path.join(project_root, "src\\inputs")

# List all files in inputs
input_files = [
    f for f in os.listdir(inputs_dir)
    if os.path.isfile(os.path.join(inputs_dir, f))
]

# Select the first input file
if input_files:
    input_file_path = os.path.join(inputs_dir, input_files[0])
    # Load the C++ code from the file using helper
    cpp_code = load_input_from_file(input_file_path)
    initiate_chat_message = user_proxy_message + "\n" + cpp_code
    user_proxy.initiate_chat(
        group_chat_manager,
        message=initiate_chat_message
    )

    # After chat is done, extract and save only the final relevant outputs
    def extract_relevant_outputs(messages, agent_patterns):
        outputs = {}
        for agent, patterns in agent_patterns.items():
            outputs[agent] = None
            for msg in reversed(messages):
                if msg.get("name") == agent and all(p in msg["content"] for p in patterns):
                    outputs[agent] = msg["content"]
                    break
        return outputs

    agent_patterns = {
        "Requirement_Engineer": ["Title:", "Requirements:"],
        "Code_Translator": ["Translated Code:", "Code", "python"],
        "Code_Validator": ["Syntax", "Semantic", "Error", "Validation Report"],  
        "Code_Tester": ["Overall Test Summary", "Test"],  
        "Critic": ["Score:", "Critique:", "Suggestions:"]
    }

    final_outputs = extract_relevant_outputs(groupchat.messages, agent_patterns)

    for name, content in final_outputs.items():
        if content:
            save_output_to_file(content, name.lower(), "output")
        else:
            print(f"No relevant output found for agent: {name}")

else:
    print("No input files found in the inputs directory.Cannot initiate the chat.")


