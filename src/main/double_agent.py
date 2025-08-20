import os
from pathlib import Path
import time

# Load the configuration loader service for the agents.
from ..services.config_loader import load_config

# Load the prompts for the agents.
from ..prompts.double_agent_prompts import re_message, translator_message, user_proxy_message, user_proxy_prompt

# Load the services for the agents.
from ..services.agent_factory import AgentFactory
from ..services.agent_helpers import extract_relevant_outputs, read_json_file, save_output_to_json_file

# Output paths (separate folder for custom sequential flow)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs' / 'double_agent_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CODE_OUT = OUTPUT_DIR / 'generated_python_code.json'
REQ_OUT = OUTPUT_DIR / 'generated_requirements.json'
TIME_LOG = OUTPUT_DIR / 'time_log.json'
INPUT_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'input_program.json'

# Static values and variables
agent_patterns = {
        "Requirement_Engineer": [r"Title:\s*.*"],
        "Code_Translator": [r'```(python|py|python3)\n(.*?)```']
    }

translations = {}
requirements = {}
time_log = {}
PHASE_ORDER = ["REQUIREMENTS", "TRANSLATION"]

# Load the configuration file path of the agents.
current_dir = Path(__file__).resolve().parent
base_dir = current_dir.parent
config_path = os.path.join(base_dir, "llm_config.json")

# Load all LLM configurations for the agents.
llm_configs = load_config(config_path)

# Create an agent factory with mistral as default, but Qwen for Code_Translator
agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.5)
# Set temperature for Qwen model
agent_factory.set_model_temperature("qwen_coder", 0.1)  # Lower temperature for more deterministic output


# WorkflowController
class WorkflowController:
    def __init__(self, phases, phase_order):
        self.phases = phases
        self.phase_order = phase_order
        self.current_phase_idx = 0
        self.round = 0

    def get_next_agent(self, agents):
        # Always return the agent for the current phase
        phase = self.phase_order[self.current_phase_idx]
        phase_agents = self.phases[phase]["agents"]
        agent = phase_agents[0] if phase_agents else None
        # Move to next phase for next call
        self.current_phase_idx = (self.current_phase_idx + 1) % len(self.phase_order)
        return agent

# Minimal local SpeakerSelector for double agent communication
class SpeakerSelector:
    def __init__(self, workflow_controller, first_agent):
        self.workflow_controller = workflow_controller
        self.first_agent = first_agent
        self.first = True

    def select_next_speaker(self, agents, messages):
        if self.first:
            self.first = False
            return self.first_agent
        return self.workflow_controller.get_next_agent(agents)

# Create the agents using the agent factory.
#Requirement Engineer
requirement_engineer = agent_factory.create_assistant(
    name="Requirement_Engineer",
    system_message=re_message,
    llm_model="qwen_coder"
)

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

# Simple group chat with a sequential agent collaboration logic.
workflow_controller = WorkflowController(PHASES, PHASE_ORDER)
speaker_selector = SpeakerSelector(workflow_controller, requirement_engineer)
input_cpp_codes = read_json_file(str(INPUT_PATH))


# Single group chat for RE -> Translator process
for key, cpp_code in list(input_cpp_codes.items()):
    print(f"Processing key: {key}")
    start_time = time.perf_counter()

    groupchat = agent_factory.create_groupchat(
        agents=[requirement_engineer, code_translator],
        speaker_selector=speaker_selector.select_next_speaker,
        max_round=4
    )
    group_manager = agent_factory.create_group_manager(groupchat=groupchat)
    user_proxy.initiate_chat(
        group_manager,
        message=user_proxy_prompt + cpp_code
    )
    output = extract_relevant_outputs(groupchat.messages, agent_patterns)
    req = output.get("Requirement_Engineer", [""])[0] if output.get("Requirement_Engineer") else ""
    code = output.get("Code_Translator", [""])[0] if output.get("Code_Translator") else ""
    end_time = time.perf_counter()
    requirements[key] = req
    translations[key] = code
    save_output_to_json_file(str(CODE_OUT), translations)
    save_output_to_json_file(str(REQ_OUT), requirements)
    # Log the time taken for this translation
    time_taken = end_time - start_time
    time_log[key] = time_taken
    save_output_to_json_file(str(TIME_LOG), time_log)

