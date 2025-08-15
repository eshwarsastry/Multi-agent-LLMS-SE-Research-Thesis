import os
from typing import Literal
from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent


class AgentFactory:
    def __init__(self, llm_configs, default_model="mistral", default_temp=0.3):
        # Store all LLM configs
        self.llm_configs = llm_configs
        self.default_model = default_model
        self.default_temp = default_temp
        self.defaults = {}

    def set_model_temperature(self, model_key: str, temperature: float):
        """Set temperature for a specific model configuration"""
        if model_key in self.llm_configs:
            self.llm_configs[model_key]["temperature"] = temperature

    def create_assistant(self, name: str, system_message: str, llm_model: str = None):
        # LLM config- use provided model or default "mistral" Ollama model
        model_key = llm_model or ("qwen_25_coder_35b_instruct" if name == "Code_Translator" else self.default_model)
        config = dict(self.llm_configs[model_key])
        
        # Apply temperature and other settings from the config
        llm_config = {"config_list": config["config_list"]}
        if "temperature" in config:
            llm_config["temperature"] = config["temperature"]
        if "timeout" in config:
            llm_config["timeout"] = config["timeout"]
        if "max_tokens" in config:
            llm_config["max_tokens"] = config["max_tokens"]
               
        return AssistantAgent(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
        )

    def create_user_proxy(self, name: str, system_messages: list):
        def _is_term(msg):
            if isinstance(msg, dict):
                content = msg.get("content")
            else:
                content = msg
            content = content or ""
            return str(content).rstrip().endswith("TERMINATE")

        return UserProxyAgent(
            name=name,
            system_message=system_messages[0],
            human_input_mode='TERMINATE',
            is_termination_msg=_is_term,
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
            llm_config=llm_config or self.llm_configs[self.default_model]
        )

