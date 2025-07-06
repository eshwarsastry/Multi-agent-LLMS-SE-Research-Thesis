from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
from services.config_loader import load_config

from prompts.re_agent_prompts import re_prompt_1
from prompts.translator_agent_prompts import translator_prompt_1
from prompts.validator_agent_prompts import validator_prompt_1
from prompts.tester_agent_prompts import code_tester_prompt_1
from prompts.critic_agent_prompts import critic_prompt_1
from prompts.user_proxy_agent_prompts import user_proxy_prompt1, user_proxy_prompt2
from prompts.manager_agent_prompts import manager_prompt_1

# Configuration for Ollama's local DeepSeek model.
config_list = load_config()

# Setting up the agents for the mulit-agent system.

# User Proxy Agent
user_proxy = UserProxyAgent(
    name="User_Proxy",
    system_message=user_proxy_prompt1,
    human_input_mode="ALWAYS",  # or "NEVER" for automated testing
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

# Manager 
manager = AssistantAgent(
    name="Manager",
    system_message=manager_prompt_1,
    llm_config={"config_list": config_list}
)

class WorkflowController:
    PHASES = {
        "REQUIREMENTS": requirement_engineer,
        "TRANSLATION": code_translator,
        "VALIDATION": validator,
        "TESTING": code_tester,
        "CRITIQUE": critic
    }
    
    def __init__(self):
        self.current_phase = "REQUIREMENTS"
        self.phase_history = []
        
    def next_phase(self, last_message):
        # Sequential phase progression
        phase_order = list(self.PHASES.keys())
        current_idx = phase_order.index(self.current_phase)
        
        # Handle validation failures
        if self.current_phase == "VALIDATION" and "errors" in last_message:
            return "TRANSLATION"  # Send back to translator
        
        # Handle test failures
        if self.current_phase == "TESTING" and "FAILURES" in last_message:
            return "TRANSLATION"  # Send back to translator
            
        # Normal progression
        if current_idx < len(phase_order) - 1:
            return phase_order[current_idx + 1]
        return "COMPLETE"
    
    def update_phase(self, last_message):
        new_phase = self.next_phase(last_message)
        if new_phase != self.current_phase:
            self.phase_history.append(self.current_phase)
            self.current_phase = new_phase
        return self.PHASES.get(new_phase, None)

# Create workflow controller
workflow_controller = WorkflowController()

def select_speaker(last_speaker, group_chat):
    last_message = group_chat.messages[-1]["content"] if group_chat.messages else ""
    
    # Manager always controls phase transitions
    if last_speaker != manager:
        manager.update_system_message(
            f"Next phase: {workflow_controller.current_phase}"
        )
        return manager
    
    # Get next agent from workflow controller
    next_agent = workflow_controller.update_phase(last_message)
    
    if not next_agent:
        # Termination condition
        if "RATING" in last_message and int(last_message.split("RATING: ")[1][0]) > 7:
            return None  # End conversation
        return manager  # Re-review if low rating
    
    # Pass required context to next agent
    if next_agent.name == "Translator":
        requirements = extract_value("REQUIREMENTS:", group_chat.messages)
        next_agent.update_system_message(f"Input requirements: {requirements}")
    
    return next_agent

# Helper function
def extract_value(key, messages):
    for msg in reversed(messages):
        if key in msg["content"]:
            return msg["content"].split(key)[1].strip()
    return ""

# Group Chat for all agents except User Proxy (which is the initiator)
groupchat = GroupChat(
    agents=[requirement_engineer, code_translator, validator, code_tester, critic, manager],
    messages=[],
    max_round=20,
    speaker_transitions_type="Disallowed",
    speaker_selection_method= select_speaker, 
    allowed_or_disallowed_speaker_transitions={
        requirement_engineer: [manager],
        code_translator: [manager],
        validator: [manager],
        code_tester: [manager],
        critic: [manager],
        manager: [requirement_engineer, code_translator, validator, code_tester, critic]  # Manager can route to anyone
    }
)

# Then, we start the conversation with the user proxy initiating the task.
user_proxy.initiate_chat(
    manager,
    message= user_proxy_prompt2,  
    groupchat=groupchat,
)