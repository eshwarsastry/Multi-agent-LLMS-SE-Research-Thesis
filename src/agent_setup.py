from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
from services.config_loader import load_config

from prompts.re_agent_prompts import re_prompt_1
from prompts.translator_agent_prompts import translator_prompt_1
from prompts.validator_agent_prompts import validator_prompt_1
from prompts.tester_agent_prompts import code_tester_prompt_1
from prompts.critic_agent_prompts import critic_prompt_1
from prompts.user_proxy_agent_prompts import user_proxy_prompt1, user_proxy_prompt2

from agent_workflow import WorkflowController, SpeakerSelector


# Load the default configuration for the agents.
config_list = load_config()

# Setting up the agents for the multi-agent system.

# User Proxy Agent
user_proxy = UserProxyAgent(
    name="User_Proxy",
    system_message=user_proxy_prompt1,
    human_input_mode="NEVER",  # Automated workflow without human input
)

# Requirement Engineer
requirement_engineer = AssistantAgent(
    name="Requirement_Engineer",
    system_message= re_prompt_1,
    llm_config={"config_list": config_list}
)

# Code Translator
code_translator = AssistantAgent(
    name="Code_Translator",
    system_message=translator_prompt_1,
    llm_config={"config_list": config_list}
)

# Code Validator
validator = AssistantAgent(
    name="Code_Validator",
    system_message=validator_prompt_1,
    llm_config={"config_list": config_list}
)

# Code Tester
code_tester = AssistantAgent(
    name="Code_Tester",
    system_message=code_tester_prompt_1,
    llm_config={"config_list": config_list}
)

# Critic
critic = AssistantAgent(
    name="Critic",
    system_message= critic_prompt_1,
    llm_config={"config_list": config_list}
)

# Define phases for the workflow
PHASES = {
    "REQUIREMENTS": requirement_engineer,
    "TRANSLATION": code_translator,
    "VALIDATION": validator,
    "PARALLEL": [code_tester, critic]  # Both tester and critic agents work in parallel
}

# Create workflow controller
workflow_controller = WorkflowController(PHASES)

# Create speaker selector
speaker_selector = SpeakerSelector(workflow_controller, requirement_engineer)

# Group Chat for all agents except User Proxy (which is the initiator)
groupchat = GroupChat(
    agents=[requirement_engineer, code_translator, validator, code_tester, critic],
    messages=[],
    max_round=20,
    speaker_transitions_type="allowed",
    speaker_selection_method= speaker_selector.select_speaker
)

# Create group chat manager
group_chat_manager = GroupChatManager(
    groupchat=groupchat,
    llm_config={"config_list": config_list}
)

# Then, we start the conversation with the user proxy initiating the task.
user_proxy.initiate_chat(
    group_chat_manager,
    message= user_proxy_prompt2
)