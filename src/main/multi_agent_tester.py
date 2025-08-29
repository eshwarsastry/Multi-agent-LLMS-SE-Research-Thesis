import os
from pathlib import Path
import time
from typing import Dict
from typing_extensions import Annotated
import traceback

# Load all required service dependencies.
from ..services.agent_helpers import read_json_file, save_output_to_json_file
from ..services.config_loader import load_config
from ..services.agent_factory import AgentFactory
from ..services.output_testing import run_python_tests_from_dataset
from ..services.multi_agent_workflow_engine import create_custom_workflow
from ..services.multi_agent_retry_checker import RetryConditionChecker

# Load the required prompts.
from ..prompts.multi_agent_prompts import (
    user_proxy_message,
    re_message,
    translator_message,
    code_tester_message,
    critic_message,
    re_prompt,
    translator_prompt_1,
    code_tester_prompt_db_tests,
    critic_prompt,
)

# Output paths with separate folder for multi-agent workflow flow-
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs' / 'multi_agent_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CODE_OUT = OUTPUT_DIR / 'generated_python_code.json'
REQ_OUT = OUTPUT_DIR / 'generated_requirements.json'
TEST_OUT = OUTPUT_DIR / 'generated_tests.json'
CRITIC_OUT = OUTPUT_DIR / 'generated_critic.json'
STATUS_OUT = OUTPUT_DIR / 'process_status.json'
TIME_LOG = OUTPUT_DIR / 'time_log.json'

INPUT_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'input_program.json'
GROUND_TRUTH_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth.json'
GROUND_TRUTH_TEST_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth_test.json'

def create_agents_with_tools():
    """Create all agents with their tools registered"""
    
    # Load config
    current_dir = Path(__file__).resolve().parent
    base_dir = current_dir.parent
    config_path = os.path.join(base_dir, "llm_config.json")
    llm_configs = load_config(config_path)

    # Create the agents using the Agent Factory
    agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.5)
    agent_factory.set_model_temperature("qwen_coder", 0.1)

    # Create agents
    requirement_engineer = agent_factory.create_assistant(
        name="Requirement_Engineer",
        system_message=re_message,
        llm_model="qwen_coder",
    )

    code_translator = agent_factory.create_assistant(
        name="Code_Translator",
        system_message=translator_message,
        llm_model="qwen_coder",
    )

    code_tester = agent_factory.create_assistant(
        name="Code_Tester",
        system_message=code_tester_message,
        llm_model="gpt-5-mini",
    )

    critic = agent_factory.create_assistant(
        name="Critic",
        system_message=critic_message,
        llm_model="qwen_coder",
    )

    user_proxy = agent_factory.create_user_proxy(
        name="User_Proxy", 
        system_messages=[user_proxy_message]
    )

    # Register tools for code_tester agent.
    _register_testing_tools(user_proxy, code_tester)

    return {
        "Requirement_Engineer": requirement_engineer,
        "Code_Translator": code_translator,
        "Code_Tester": code_tester,
        "Critic": critic,
        "User_Proxy": user_proxy,
    }

def _register_testing_tools(user_proxy, code_tester):
    """Register testing tools"""
    def execute_and_compare_tests(
        program_key: Annotated[str, "Program identifier string"],
        translated_code: Annotated[str, "Python program string translated"],
    ) -> Dict:
        ground_tests = read_json_file(str(GROUND_TRUTH_TEST_PATH))
        py_tests = ground_tests.get(program_key, "")
        return run_python_tests_from_dataset(
            translated_code=translated_code,
            py_tests=py_tests
        )

    # Register under both names for compatibility
    user_proxy.register_for_execution(name="execute_and_compare_tests")(execute_and_compare_tests)
    user_proxy.register_for_execution(name="run_and_compare_tests")(execute_and_compare_tests)
    
    code_tester.register_for_llm(
        name="execute_and_compare_tests",
        description="Run tests on the translated Python code and compare results",
    )(execute_and_compare_tests)
    code_tester.register_for_llm(
        name="run_and_compare_tests",
        description="Run tests on the translated Python code and compare results",
    )(execute_and_compare_tests)

def main(max_items: int | None = None):
    # Orchestration phase ->speakers mapping
    phase_speakers = {
        "TRANSLATION": ["Code_Translator"],
        "TESTING": ["Code_Tester"],
        "REVIEW": ["Critic"],
        "COMPLETE": [],
    }

    # Phase execution order
    phase_order = ["TRANSLATION", "TESTING", "REVIEW", "COMPLETE"]

    # Phases to execute
    execution_phases = ["TRANSLATION", "TESTING", "REVIEW"]

    # Patterns to extract relevant outputs from the agent chat history
    agent_patterns = {
        "Requirement_Engineer": r"Title:\s*.*",
        "Code_Translator": r"```(python|py|python3)\n(.*?)```",
        "Code_Tester": r"```\n(text|test_results)*\n(.*?)```",
        "Critic": r"```(text|review_block)\n(.*?)```",
    }

    # Agent access patterns for shared workspace
    agent_access_patterns = {
        "Code_Translator": ["original_cpp_code", "test_results"],
        "Code_Tester": ["translated_code", "program_key"],
        "Critic": ["translated_code", "test_results", "validation_results"],
        "User_Proxy": []  # Can access entire context from shared workspace
    }

    # Phase configurations
    phase_configs = {
        "TRANSLATION": {
            "default_agent": "Code_Translator",
            "context_keys": ["original_cpp_code", "translated_code", "test_results"],
            "prompt_template": translator_prompt_1,
            "prompt_kwargs": lambda ctx: {
                "requirements": ctx.get("requirements", ""),
                "cpp_code": ctx.get("original_cpp_code", ""),
                "python_code": ctx.get("translated_code", ""),
                "test_results": ctx.get("test_results", "")
            },
            "output_key": "translated_code",
            "max_turns": 1
        },
        "TESTING": {
            "default_agent": "Code_Tester",
            "context_keys": ["translated_code", "program_key"],
            "prompt_template": code_tester_prompt_db_tests,
            "prompt_kwargs": lambda ctx: {
                "python_code": ctx.get("translated_code", ""),
                "program_key": ctx.get("program_key", "")
            },
            "output_key": "test_results",
            "max_turns": 2,
            "extract_from_chat": True  
        },
        "REVIEW": {
            "default_agent": "Critic",
            "context_keys": ["translated_code", "test_results"],
            "prompt_template": critic_prompt,
            "prompt_kwargs": lambda ctx: {
                "python_code": ctx.get("translated_code", ""),
                "test_results": ctx.get("test_results", "")
            },
            "output_key": "critic_review",
            "max_turns": 1,
            "extract_from_chat": True  
        }
    }

    # Retry configuration with handler functions
    retry_config = {
        "enabled": True,
        "max_retries": 1,
        "condition_handlers": {
            "validation_check": RetryConditionChecker.validation_check,
            "critic_score_check": RetryConditionChecker.critic_score_check,
            "tester_summary_check": RetryConditionChecker.tester_summary_check,
            "custom_check": RetryConditionChecker.custom_check,
        },
        "retry_conditions": [
            # {
            #     "type": "tester_summary_check", 
            #     "workspace_key": "tester_summary",
            #     "failure_patterns": ["fail", "error"],
            #     "retry_message": "Test summary indicates failure"
            # },
            {
                "type": "critic_score_check", 
                "workspace_key": "critic_review",
                "min_score": 6,
                "retry_message": "low critic score"
            },
            {
                "type": "validation_check",
                "workspace_key": "validation_results",
                "error_patterns": [
                    "syntax errors: none",
                    "compilation issues: none",
                    "structural problems: none"
                ],
                "retry_message": "validation errors detected"
            },
        ]
    }

    # Create pre-configured agents
    agents = create_agents_with_tools()

    # Create workflow with all configurations
    agents, run = create_custom_workflow(
        agents=agents,
        phase_speakers=phase_speakers,
        phase_order=phase_order,
        execution_phases=execution_phases,
        agent_patterns=agent_patterns,
        agent_access_patterns=agent_access_patterns,
        phase_configs=phase_configs,
        retry_config=retry_config,
    )

    # Load input data
    input_cpp_codes = read_json_file(str(INPUT_PATH))
    
    # Variables used for storing the extracted results.
    translations = {}
    requirements = {}
    validations = {}
    tests = {}
    critic_reviews = {}
    status = {}
    time_log = {}
    # Process limiting number of programs translated if specified in calling the main method.
    items_to_process = list(input_cpp_codes.items())
    
    if max_items:
        items_to_process = items_to_process[:max_items]

    for key, cpp_code in items_to_process:
        print(f"Translating C++ code for key: {key}")
        start_time = time.perf_counter()
        try:
            # Run the workflow
            chat_history, outputs = run(cpp_code, key)

            has_any_output = any(outputs.get(key) for key in ['translated_code', 'requirements', 'validation_results', 'test_results', 'critic_review'])
            
            if has_any_output:
                status[key] = "Success"
                end_time = time.perf_counter()
                time_taken = end_time - start_time
                time_log[key] = time_taken
                # Collect outputs
                if outputs.get('translated_code'):
                    translations[key] = outputs['translated_code']
                if outputs.get('requirements'):
                    requirements[key] = outputs['requirements']
                if outputs.get('validation_results'):
                    validations[key] = outputs['validation_results']
                if outputs.get('test_results'):
                    tests[key] = outputs['test_results']
                if outputs.get('critic_review'):
                    critic_reviews[key] = outputs['critic_review']
            else:
                status[key] = "Failed"
        except Exception as e:
            print(f"Error processing key {key}: {e}")
            status[key] = "Error"
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            end_time = time.perf_counter()
            time_taken = end_time - start_time
            time_log[key] = time_taken
            # Continue with next item
            continue
    # Save outputs
    save_output_to_json_file(str(TIME_LOG), time_log)
    save_output_to_json_file(str(CODE_OUT), translations)
    save_output_to_json_file(str(REQ_OUT), requirements)
    save_output_to_json_file(str(TEST_OUT), tests)
    save_output_to_json_file(str(CRITIC_OUT), critic_reviews)
    save_output_to_json_file(str(STATUS_OUT), status)

if __name__ == '__main__':
    main()


