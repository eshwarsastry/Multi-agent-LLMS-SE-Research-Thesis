import os
from typing import Literal
from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent


class AgentFactory:
    def __init__(self, llm_config_list, default_model=None, default_temp=None):
        # Load base config loaded from file
        self.base_config = {"config_list": llm_config_list}
        # Optional overrides
        self.defaults = {}

    def create_assistant(self, name: str, system_message: str, tools: list):
        config = dict(self.base_config)
        # tools can be added if needed
        return AssistantAgent(
            name=name,
            system_message=system_message,
            llm_config=config
        )

    def create_user_proxy(self, name: str, system_messages: list):
        # Accepts list for few shots if needed
        return UserProxyAgent(
            name=name,
            system_message=system_messages[0],
            human_input_mode= 'TERMINATE',
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "agent_code_execution", "use_docker": True},
        )

    def create_groupchat(self, agents, speaker_selector, max_round=20):
        return GroupChat(
            agents=agents,
            messages=[],
            max_round=max_round,
            speaker_transitions_type="allowed",
            speaker_selection_method=speaker_selector
        )

    def create_group_manager(self, groupchat, llm_config=None):
        return GroupChatManager(
            groupchat=groupchat,
            llm_config=llm_config or self.base_config
        )

