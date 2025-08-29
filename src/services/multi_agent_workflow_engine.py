from typing import Dict, List, Tuple

from .agent_workflow import WorkflowController
from .agent_helpers import extract_relevant_outputs
from .shared_workspace import SharedWorkspace

def create_custom_workflow(
    agents: Dict,
    phase_speakers: Dict[str, List[str]],
    phase_order: List[str],
    execution_phases: List[str],
    agent_patterns: Dict[str, str],
    agent_access_patterns: Dict[str, List[str]],
    phase_configs: Dict[str, Dict],
    retry_config: Dict = None
    ):
    """Create a custom multi-agent workflow with pure execution logic"""
    
    # Default retry config if none provided
    default_retry_config = {
        "enabled": False,
        "max_retries": 3,
        "retry_conditions": []
    }
    retry_config = retry_config or default_retry_config
    
    # Create workflow controller
    controller = WorkflowController(
        phase_speakers=phase_speakers, 
        phase_order=phase_order
    )

    def run_fn(cpp_code: str, key: str = "default") -> Tuple[List[dict], Dict[str, str]]:
        """Core workflow execution logic"""
        
        # Initialize shared workspace
        workspace = SharedWorkspace("translation_workflow", agent_access_patterns)
        workspace.write("original_cpp_code", cpp_code, "System")
        workspace.write("program_key", key, "System")
        chat_history: List[dict] = []
        max_retries = retry_config.get("max_retries", 1)
        attempt = 1

        while attempt <= max_retries:
            # Execute all configured phases
            for phase_name in execution_phases:
                _execute_generic_phase(
                    phase_name=phase_name,
                    phase_config=phase_configs[phase_name],
                    agents=agents,
                    controller=controller,
                    workspace=workspace,
                    agent_patterns=agent_patterns,
                    chat_history=chat_history
                )
            
            # Check retry conditions only if retry is enabled
            if retry_config.get("enabled", False):
                should_retry, attempt = _check_retry_conditions(
                    workspace, attempt, max_retries, retry_config
                )
                if not should_retry:
                    break
            else:
                # No retry logic - exit after first execution
                break

        return chat_history, workspace.get_all_outputs()

    return agents, run_fn

def _execute_generic_phase(
    phase_name: str,
    phase_config: Dict,
    agents: Dict,
    controller: WorkflowController,
    workspace: SharedWorkspace,
    agent_patterns: Dict[str, str],
    chat_history: List[dict]
):
    """Generic phase execution method"""
    
    # Get the agent for this phase
    speakers = controller.get_speakers_for_phase(phase_name) or [phase_config["default_agent"]]
    agent_name = speakers[0]
    
    # Get context for this agent
    context = workspace.get_context_for_agent(agent_name, phase_config["context_keys"])
    
    # Build the prompt message
    prompt_kwargs = phase_config["prompt_kwargs"](context)
    message = phase_config["prompt_template"].format(**prompt_kwargs)
    
    # Execute the chat
    chat_result = agents["User_Proxy"].initiate_chat(
        agents.get(agent_name),
        message=message,
        max_turns=phase_config["max_turns"],
    )
    chat_history.extend(getattr(chat_result, "chat_history", []))
    
    # Extract and store the output
    if phase_config.get("extract_from_chat", False):
        # Special handling - extract from chat directly
        output_text = next(
            (m.get("content", "") for m in reversed(getattr(chat_result, "chat_history", [])) 
             if m.get("name") == agent_name),
            "",
        )
    else:
        # Standard extraction using patterns
        outputs = extract_relevant_outputs(
            getattr(chat_result, "chat_history", []),
            {agent_name: agent_patterns[agent_name]}
        )
        output_text = (outputs.get(agent_name, []) or [""])[0]
    
    # Write to workspace
    workspace.write(phase_config["output_key"], output_text, agent_name)

def _check_retry_conditions(workspace, attempt, max_retries, retry_config):
    """Check if workflow should retry based on configured conditions"""
    
    should_retry = False
    feedback_messages = []
    retry_conditions = retry_config.get("retry_conditions", [])
    condition_handlers = retry_config.get("condition_handlers", {})
    
    # Check each configured retry condition
    for condition in retry_conditions:
        condition_type = condition.get("type")
        
        # Get the handler for this condition type
        handler = condition_handlers.get(condition_type)
        
        if handler and callable(handler):
            if handler(workspace, condition):
                should_retry = True
                message = condition.get("retry_message", f"{condition_type} condition met")
                feedback_messages.append(message)
    
    # Handle retry logic
    if should_retry:
        attempt += 1
        if attempt <= max_retries:
            feedback = "; ".join(feedback_messages)
            workspace.write("retry_feedback", feedback, "System")
            return True, attempt
    
    return False, attempt

