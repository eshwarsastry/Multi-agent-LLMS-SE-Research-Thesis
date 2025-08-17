import os
from pathlib import Path
import time
from typing import Dict
from typing_extensions import Annotated
import traceback

# Load all required service dependencies.
from ..services.agent_helpers import read_json_file, save_output_to_json_file
from ..services.result_evaluation import evaluate_codebleu_for_pairs, print_codebleu_results
from ..services.config_loader import load_config
from ..services.agent_factory import AgentFactory
from ..services.output_validation import validate_python_syntax
from ..services.output_testing import run_and_compare_tests as run_and_compare_tests_service
from ..services.multi_agent_workflow_engine import create_custom_workflow
from ..services.multi_agent_retry_checker import RetryConditionChecker

# Load the required prompts.
from ..prompts.multi_agent_prompts import (
    user_proxy_message,
    re_message,
    translator_message,
    validator_message,
    code_tester_message,
    critic_message,
    re_prompt,
    translator_prompt,
    validator_prompt,
    code_tester_prompt,
    critic_prompt,
)

# Output paths with separate folder for multi-agent workflow flow-
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs' / 'multi_agent_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CODE_OUT = OUTPUT_DIR / 'generated_python_code.json'
REQ_OUT = OUTPUT_DIR / 'generated_requirements.json'
VALID_OUT = OUTPUT_DIR / 'generated_validator.json'
TEST_OUT = OUTPUT_DIR / 'generated_tests.json'
CRITIC_OUT = OUTPUT_DIR / 'generated_critic.json'
STATUS_OUT = OUTPUT_DIR / 'process_status.json'
TIME_LOG = OUTPUT_DIR / 'time_log.json'

INPUT_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'input_program.json'
GROUND_TRUTH_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth.json'


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

    code_validator = agent_factory.create_assistant(
        name="Code_Validator",
        system_message=validator_message,
        llm_model="llama_instruct",
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

    # Register tools for validator and code_tester agents.
    _register_validation_tool(user_proxy, code_validator)
    _register_testing_tools(user_proxy, code_tester)

    return {
        "Requirement_Engineer": requirement_engineer,
        "Code_Translator": code_translator,
        "Code_Validator": code_validator,
        "Code_Tester": code_tester,
        "Critic": critic,
        "User_Proxy": user_proxy,
    }

def _register_validation_tool(user_proxy, code_validator):
    """Register validation tool"""
    def validate_translated_code(
        translated_code: Annotated[str, "Python program string translated"]
    ) -> Dict:
        return validate_python_syntax(translated_code=translated_code)

    user_proxy.register_for_execution(name="validate_translated_code")(
        validate_translated_code
    )
    code_validator.register_for_llm(
        name="validate_translated_code",
        description="Validate the translated Python code to check if it compiles",
    )(validate_translated_code)

def _register_testing_tools(user_proxy, code_tester):
    """Register testing tools"""
    def execute_and_compare_tests(
        legacy_code: Annotated[str, "C++ program string provided"],
        translated_code: Annotated[str, "Python program string translated"],
        cpp_tests: Annotated[str, "C++ test methods"],
        py_tests: Annotated[str, "Python test methods"],
    ) -> Dict:
        return run_and_compare_tests_service(
            legacy_code=legacy_code,
            translated_code=translated_code,
            cpp_tests=cpp_tests,
            py_tests=py_tests,
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
        "REQUIREMENTS": ["Requirement_Engineer"],
        "TRANSLATION": ["Code_Translator"],
        "VALIDATION": ["Code_Validator"],
        "TESTING": ["Code_Tester"],
        "REVIEW": ["Critic"],
        "COMPLETE": [],
    }

    # Phase execution order
    phase_order = ["REQUIREMENTS", "TRANSLATION", "VALIDATION", "TESTING", "REVIEW", "COMPLETE"]

    # Phases to execute
    execution_phases = ["REQUIREMENTS", "TRANSLATION", "VALIDATION", "TESTING", "REVIEW"]

    # Patterns to extract relevant outputs from the agent chat history
    agent_patterns = {
        "Requirement_Engineer": r"Title:\s*.*",
        "Code_Translator": r"```(python|py|python3)\n(.*?)```",
        "Code_Validator": r"(Validation Summary:?\s*.*)",
        "Code_Tester": r"Test Summary:\s*.*",
        "Critic": r"(Score:?\s*\d+|Critique:?\s*.*|Suggestions?:?\s*.*)",
    }

    # Agent access patterns for shared workspace
    agent_access_patterns = {
        "Requirement_Engineer": ["original_cpp_code"],
        "Code_Translator": ["requirements", "original_cpp_code", "feedback"],
        "Code_Validator": ["translated_code"],
        "Code_Tester": ["original_cpp_code", "translated_code", "requirements"],
        "Critic": ["translated_code", "test_results", "validation_results"],
        "User_Proxy": []  # Can access entire context from shared workspace
    }

    # Phase configurations
    phase_configs = {
        "REQUIREMENTS": {
            "default_agent": "Requirement_Engineer",
            "context_keys": ["original_cpp_code"],
            "prompt_template": re_prompt,
            "prompt_kwargs": lambda ctx: {"cpp_code": ctx.get("original_cpp_code", "")},
            "output_key": "requirements",
            "max_turns": 1
        },
        "TRANSLATION": {
            "default_agent": "Code_Translator", 
            "context_keys": ["requirements", "original_cpp_code"],
            "prompt_template": translator_prompt,
            "prompt_kwargs": lambda ctx: {
                "requirements": ctx.get("requirements", ""),
                "cpp_code": ctx.get("original_cpp_code", "")
            },
            "output_key": "translated_code",
            "max_turns": 1
        },
        "VALIDATION": {
            "default_agent": "Code_Validator",
            "context_keys": ["translated_code"],
            "prompt_template": validator_prompt,
            "prompt_kwargs": lambda ctx: {"python_code": ctx.get("translated_code", "")},
            "output_key": "validation_results",
            "max_turns": 2
        },
        "TESTING": {
            "default_agent": "Code_Tester",
            "context_keys": ["original_cpp_code", "translated_code"],
            "prompt_template": code_tester_prompt,
            "prompt_kwargs": lambda ctx: {
                "cpp_code": ctx.get("original_cpp_code", ""),
                "python_code": ctx.get("translated_code", "")
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
        "max_retries": 3,
        "condition_handlers": {
            "validation_check": RetryConditionChecker.validation_check,
            "critic_score_check": RetryConditionChecker.critic_score_check,
            "custom_check": RetryConditionChecker.custom_check,
        },
        "retry_conditions": [
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
            {
                "type": "critic_score_check", 
                "workspace_key": "critic_review",
                "min_score": 6,
                "retry_message": "low critic score"
            }
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
        retry_config=retry_config
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
            chat_history, outputs = run(cpp_code)

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
    save_output_to_json_file(str(VALID_OUT), validations)
    save_output_to_json_file(str(TEST_OUT), tests)
    save_output_to_json_file(str(CRITIC_OUT), critic_reviews)
    save_output_to_json_file(str(STATUS_OUT), status)

if __name__ == '__main__':
    main(2)
