from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
from services.config_loader import load_config

# Configuration for Ollama's local DeepSeek model
config_list = load_config()

# Configuration for the agents
# User Proxy Agent
user_proxy = UserProxyAgent(
    name="User_Proxy",
    system_message="A human user proxy. Provides the legacy code and receives the final modern code.",
    human_input_mode="ALWAYS",  # or "NEVER" for automated testing
)
# Requirement Engineer
requirement_engineer = AssistantAgent(
    name="Requirement_Engineer",
    system_message="You are a Requirement Engineer. You extract requirements from legacy code and specify modern requirements. Return the requirements as a markdown document.",
    llm_config={"config_list": config_list}
)
# Code Translator
code_translator = AssistantAgent(
    name="Code_Translator",
    system_message="You are a Code Translator. You translate legacy code to modern code based on the requirements. Return the translated code.",
    llm_config={"config_list": config_list}
)

# Syntactic Fixer
syntactic_fixer = AssistantAgent(
    name="Code_Translator",
    system_message="You are a Syntactic fixer. You test the translated code for syntax errors. " \
    "If there are any syntax errors in the code, you correct them." \
    "Return the syntax error free code.",
    llm_config={"config_list": config_list}
)

# Semantic Fixer
semantic_fixer = AssistantAgent(
    name="Semantic_Fixer",
    system_message="You are a Semantic fixer. You test the translated code for semantic errors. " \
    "If there are any semantic errors in the code, you correct them." \
    "Return the semantic error free code.",
    llm_config={"config_list": config_list}
)

# Critic
critic = AssistantAgent(
    name="Critic",
    system_message="You are a Critic. You review the translated code and provide feedback on its quality, " \
    "adherence to requirements, and potential improvements. Return your feedback as a markdown document.",
    llm_config={"config_list": config_list}
)

# Manager
manager = AssistantAgent(   
    name="Manager",
    system_message="You are a Manager. You oversee the workflow, assign tasks to agents, and ensure the final code meets the requirements.",
    llm_config={"config_list": config_list}
)

# Group Chat for all agents except User Proxy (which is the initiator)
groupchat = GroupChat(
    agents=[requirement_engineer, code_translator, syntactic_fixer, semantic_fixer, critic, manager],
    messages=[],
    max_round=20,
    speaker_selection_method="Auto", 
)

# Manager (as group chat manager)
manager = GroupChatManager(
    groupchat=groupchat,
    system_message="You are the Manager. Assign tasks to the appropriate agents based on the organisational roles and ensure the workflow is followed.",
    llm_config={"config_list": config_list}
)

# Then, we start the conversation with the user proxy initiating the task.
user_proxy.initiate_chat(
    manager,
    message="Here is my legacy code in .NET that needs to be converted to python:\n" \
    "using System;"\
    "using System.IO; " \
    "using System.Text;" \
    "public class HelloWorld" \
    "{" \
    "    public static void Main(string[] args)" \
    "    {" \
    "        Console.WriteLine(\"Hello, World!\");" \
    "    }" \
    "}"
)