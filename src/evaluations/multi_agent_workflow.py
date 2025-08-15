from pathlib import Path
import os
from typing import Dict, List, Tuple
from typing_extensions import Annotated
import re as _re
# Load all the services
from ..services.agent_workflow import WorkflowController
from ..services.output_testing import run_and_compare_tests as run_and_compare_tests_service
from ..services.config_loader import load_config
from ..services.agent_factory import AgentFactory
from ..services.agent_helpers import extract_relevant_outputs
from ..services.output_validation import validate_python_syntax
from ..services.shared_workspace import SharedWorkspace
# Load all the required prompts
from ..prompts.multi_agent_prompts import (
    user_proxy_message,
    re_message,
    re_prompt,
    translator_message,
    validator_message,
    code_tester_message,
    critic_message,
    translator_prompt,
    validator_prompt,
    code_tester_prompt,
    critic_prompt,
)

def create_custom_workflow(
    phase_speakers: Dict[str, List[str]] | None = None,
    phase_order: List[str] | None = None,
    agent_patterns: Dict[str, str] | None = None,
):

    # Load config
    current_dir = Path(__file__).resolve().parent
    base_dir = current_dir.parent
    config_path = os.path.join(base_dir, "llm_config.json")
    llm_configs = load_config(config_path)

    # Create the agents using the Agent Factory.
    agent_factory = AgentFactory(llm_configs, default_model="mistral", default_temp=0.5)
    agent_factory.set_model_temperature("qwen_25_coder_35b_instruct", 0.1)

    # RE agent
    requirement_engineer = agent_factory.create_assistant(
        name="Requirement_Engineer",
        system_message=re_message    ,
        llm_model="qwen_25_coder_35b_instruct",
    )

    # Translator agent
    code_translator = agent_factory.create_assistant(
        name="Code_Translator",
        system_message=translator_message,
        llm_model="qwen_25_coder_35b_instruct",
    )

    # Code Validator agent
    code_validator = agent_factory.create_assistant(
        name="Code_Validator",
        system_message=validator_message,
        llm_model="llama_31_70b_instruct",
    )

    # Code Tester agent
    code_tester = agent_factory.create_assistant(
        name="Code_Tester",
        system_message=code_tester_message,
        llm_model="gpt-5-mini",
    )

    # Critic agent
    critic = agent_factory.create_assistant(
        name="Critic",
        system_message=critic_message,
        llm_model="qwen_25_coder_35b_instruct",
    )

    # User Proxy agent
    user_proxy = agent_factory.create_user_proxy(
        name="User_Proxy", system_messages=[user_proxy_message]
    )

    # Tool registration to check for syntax errors in the translated code
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

    # Tool registration for test execution and comparison
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

    # Register under both names for compatibility with different prompts
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

    agents = {
        "Requirement_Engineer": requirement_engineer,
        "Code_Translator": code_translator,
        "Code_Validator": code_validator,
        "Code_Tester": code_tester,
        "Critic": critic,
        "User_Proxy": user_proxy,
    }

    controller = WorkflowController(
        phase_speakers=phase_speakers, phase_order=phase_order
    )

    def run_fn(cpp_code: str) -> Tuple[List[dict], Dict[str, List[str]]]:
        # Define agent access patterns for the shared workspace
        agent_access_patterns = {
            "Requirement_Engineer": ["original_cpp_code"],
            "Code_Translator": ["requirements", "original_cpp_code", "feedback"],
            "Code_Validator": ["translated_code"],
            "Code_Tester": ["original_cpp_code", "translated_code", "requirements"],
            "Critic": ["translated_code", "test_results", "validation_results"],
            "User_Proxy": [] 
        }
        
        # Initialize shared workspace with agent access patterns
        workspace = SharedWorkspace("translation_workflow", agent_access_patterns)
        workspace.write("original_cpp_code", cpp_code, "System")
        
        chat_history: List[dict] = []
        max_retries = 3
        attempt = 0

        while attempt <= max_retries:
            # 1) Requirements Phase
            req_speakers = controller.get_speakers_for_phase("REQUIREMENTS") or ["Requirement_Engineer"]
            req_agent_name = req_speakers[0]
            
            # Get context from workspace
            context = workspace.get_context_for_agent(req_agent_name, ["original_cpp_code"])
            
            requirements_phase = agents["User_Proxy"].initiate_chat(
                agents.get(req_agent_name, requirement_engineer),
                message=re_prompt.format(cpp_code=context.get("original_cpp_code", "")),
                max_turns=1,
            )
            chat_history.extend(getattr(requirements_phase, "chat_history", []))
            
            # Extract and store requirements in workspace
            req_outputs = extract_relevant_outputs(
                getattr(requirements_phase, "chat_history", []),
                {"Requirement_Engineer": agent_patterns["Requirement_Engineer"]}
            )
            requirements_text = (req_outputs.get("Requirement_Engineer", []) or [""])[0]  # Extract first element
            workspace.write("requirements", requirements_text, "Requirement_Engineer")

            # 2) Translation Phase
            tr_speakers = controller.get_speakers_for_phase("TRANSLATION") or ["Code_Translator"]
            tr_agent_name = tr_speakers[0]
            
            # Get context from workspace
            context = workspace.get_context_for_agent(tr_agent_name, ["requirements", "original_cpp_code"])
            
            translation_phase = agents["User_Proxy"].initiate_chat(
                agents.get(tr_agent_name, code_translator),
                message=translator_prompt.format(
                    requirements=context.get("requirements", ""),
                    cpp_code=context.get("original_cpp_code", "")
                ),
                max_turns=1,
            )
            chat_history.extend(getattr(translation_phase, "chat_history", []))

            # Extract and store translation
            t_outputs = extract_relevant_outputs(
                getattr(translation_phase, "chat_history", []), 
                {"Code_Translator": agent_patterns["Code_Translator"]}
            )
            translated_code = (t_outputs.get("Code_Translator", []) or [""])[0]  
            workspace.write("translated_code", translated_code, "Code_Translator")

            # 3) Validation Phase
            val_speakers = controller.get_speakers_for_phase("VALIDATION") or ["Code_Validator"]
            val_agent_name = val_speakers[0]
            
            context = workspace.get_context_for_agent(val_agent_name, ["translated_code"])

            validation_phase = agents["User_Proxy"].initiate_chat(
                agents.get(val_agent_name, code_validator),
                message=validator_prompt.format(python_code=context.get("translated_code", "")),
                max_turns=2,
            )
            chat_history.extend(getattr(validation_phase, "chat_history", []))
            validation_outputs = extract_relevant_outputs(
                getattr(validation_phase, "chat_history", []), 
                {"Code_Validator": agent_patterns["Code_Validator"]}
            )
            validation_results = (validation_outputs.get("Code_Validator", []) or [""])[0] 
            workspace.write("validation_results", validation_results, "Code_Validator")

            # 4) Testing Phase  
            test_speakers = controller.get_speakers_for_phase("TESTING") or ["Code_Tester"]
            test_agent_name = test_speakers[0]
            
            context = workspace.get_context_for_agent(test_agent_name, ["original_cpp_code", "translated_code"])
            
            testing_phase = agents["User_Proxy"].initiate_chat(
                agents.get(test_agent_name, code_tester),
                message=code_tester_prompt.format(
                    cpp_code=context.get("original_cpp_code", ""),
                    python_code=context.get("translated_code", "")
                ),
                max_turns=2,
            )
            chat_history.extend(getattr(testing_phase, "chat_history", []))

            tester_outputs = extract_relevant_outputs(
                getattr(testing_phase, "chat_history", []), 
                {"Code_Tester": agent_patterns["Code_Tester"]}
            )
            test_results = (tester_outputs.get("Code_Tester", []) or [""])[0]
            workspace.write("test_results", test_results, "Code_Tester")

            # 5) Review Phase
            rev_speakers = controller.get_speakers_for_phase("REVIEW") or ["Critic"]
            rev_agent_name = rev_speakers[0]
            
            context = workspace.get_context_for_agent(rev_agent_name, ["translated_code", "test_results"])

            critic_phase = agents["User_Proxy"].initiate_chat(
                agents.get(rev_agent_name, critic),
                message=critic_prompt.format(
                    python_code=context.get("translated_code", ""),
                    test_results=context.get("test_results", "")
                ),
                max_turns=1,
            )
            chat_history.extend(getattr(critic_phase, "chat_history", []))

            # Check retry conditions using workspace data
            validation_data = workspace.read("validation_results")
            
            # Parse text-based validation results
            has_validation_error = True  # Default to error if validation data is missing
            if validation_data:
                validation_text = str(validation_data).lower()
                # Check if all error categories show "none"
                has_syntax_errors = "syntax errors: none" not in validation_text
                has_compilation_issues = "compilation issues: none" not in validation_text
                has_structural_problems = "structural problems: none" not in validation_text
                
                # Validation passes only if all error types are "none"
                has_validation_error = has_syntax_errors or has_compilation_issues or has_structural_problems
            
            # Extract critic score and store
            critic_text = next(
                (m.get("content", "") for m in reversed(getattr(critic_phase, "chat_history", [])) if m.get("name") == "Critic"),
                "",
            )
            score = None
            m_score = _re.search(r"Score\s*[:\-]?\s*(\d+)", critic_text, _re.IGNORECASE)
            if m_score:
                try:
                    score = int(m_score.group(1))
                except Exception:
                    score = None

            workspace.write("critic_review", critic_text, "Critic")

            # Retry logic
            if has_validation_error or (score is not None and score < 7):
                attempt += 1
                if attempt > max_retries:
                    break
                # Add feedback to workspace for next iteration
                feedback = "validation errors detected" if has_validation_error else f"low critic score: {score}"
                workspace.write("Error", feedback, "System")
                continue
            else:
                break

        # Return final results from workspace
        return chat_history, workspace.get_all_outputs()

    return agents, run_fn

