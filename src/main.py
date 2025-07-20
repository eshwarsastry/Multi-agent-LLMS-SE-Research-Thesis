import os

# Load the configuration loader service for the agents.
from services.config_loader import load_config

# Load the prompts for the agents.
from prompts.re_agent_prompts import re_prompt_1
from prompts.translator_agent_prompts import translator_prompt_1
from prompts.validator_agent_prompts import validator_prompt_1
from prompts.tester_agent_prompts import code_tester_prompt_1
from prompts.critic_agent_prompts import critic_prompt_1
from prompts.user_proxy_agent_prompts import user_proxy_prompt1, user_proxy_prompt2

# Load the services for the agents.
from services.agent_workflow import WorkflowController
from services.agent_speaker_selector import SpeakerSelector
from services.agent_factory import AgentFactory
from services.output_testing import run_cpp_code, run_python_code
from services.agent_helpers import extract_relevant_outputs, load_input_from_file, save_output_to_file

# Load the configuration file path of the agents.
base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "llm_config.json")

# Load the default configuration for the agents.
config_list = load_config(config_path)

# Create an agent factory.
agent_factory = AgentFactory(config_list, default_temp=0.5)

# Create the agents using the agent factory.

# Requirement Engineer
requirement_engineer = agent_factory.create_assistant(
    name="Requirement_Engineer",
    system_message=re_prompt_1,
    tools=[]
)

# Code Translator
code_translator = agent_factory.create_assistant(
    name="Code_Translator",
    system_message=translator_prompt_1,
    tools=[]
)

# Code Validator
code_validator = agent_factory.create_assistant(
    name="Code_Validator",
    system_message=validator_prompt_1,
    tools=[]
)

# Code Tester
code_tester = agent_factory.create_assistant(
    name="Code_Tester",
    system_message=code_tester_prompt_1,
    tools=[]
)

# Critic
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
code_tester.register_for_llm(name="run_cpp_code", description="Run C++ code")(run_cpp_code)
code_tester.register_for_llm(name="run_python_code", description="Run Python code")(run_python_code)

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="run_cpp_code")(run_cpp_code)
user_proxy.register_for_execution(name="run_python_code")(run_python_code)
# Register all relevant functions to this single proxy
"""user_proxy.register_function(
    function_map={
        "run_cpp_code": run_cpp_code,
        "run_python_code": run_python_code,
        # Also include your validation functions here if they use the same proxy
        # "validate_python_syntax": validate_python_syntax,
        # "validate_cpp_syntax": validate_cpp_syntax,
    }
)"""

"""
# Register the custom reply function for the Tester_Agent's interaction with the consolidated proxy
user_proxy.register_auto_reply_function(
    code_tester,
    reply_func=custom_tester_executor_reply
) """

# Define phases for the workflow
PHASES = {
    "REQUIREMENTS": requirement_engineer,
    "TRANSLATION": code_translator,
    "Validation": code_validator, #Both tester and validator agents work in parallel
    "TESTING": code_tester,
    "REVIEW": critic 
}


# Create workflow controller
workflow_controller = WorkflowController(PHASES)

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
    groupchat=groupchat,
    llm_config={"config_list": config_list}
)

# Get the directory containing this script
base_dir = os.path.dirname(os.path.abspath(__file__))
inputs_dir = os.path.join(base_dir, "inputs")

# List all files in the inputs directory
input_files = [f for f in os.listdir(inputs_dir) if os.path.isfile(os.path.join(inputs_dir, f))]

# Select the first input file
if input_files:
    input_file_path = os.path.join(inputs_dir, input_files[0])
    # Read the C++ code from the file
    with open(input_file_path, 'r', encoding='utf-8') as f:
        cpp_code = f.read()
    

    initiate_chat_message = user_proxy_prompt2 + "\n" + cpp_code
    user_proxy.initiate_chat(
        group_chat_manager,
        message= initiate_chat_message
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
        "Code_Translator": ["Title:", "Translated Code:"],
        "Code_Validator": ["Syntax", "Semantic", "Error"],  
        "Code_Tester": ["Overall Test Summary"],  
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


