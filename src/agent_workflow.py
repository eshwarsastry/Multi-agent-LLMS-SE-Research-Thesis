from services.agent_helpers import extract_value, save_requirements_to_file

class WorkflowController:
    def __init__(self, phases):
        self.PHASES = phases
        self.current_phase = "REQUIREMENTS"
        self.phase_history = []
        
    def next_phase(self, last_message):
        phase_order = list(self.PHASES.keys())
        current_idx = phase_order.index(self.current_phase)
        
        # Handle validation failures
        if self.current_phase == "VALIDATION" and "errors" in last_message:
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
        
        # Return the agent for the current phase
        return self.PHASES.get(self.current_phase, None)

# Speaker Selector class for the group chat.
class SpeakerSelector:
    def __init__(self, workflow_controller, requirement_engineer):
        self.workflow_controller = workflow_controller
        self.requirement_engineer = requirement_engineer
    
    def select_speaker(self, last_speaker, group_chat):
        """Speaker selection function for the group chat"""
        last_message = group_chat.messages[-1]["content"] if group_chat.messages else ""
        
        # Get current phase agent
        current_agent = self.workflow_controller.PHASES.get(self.workflow_controller.current_phase, None)
        
        # Check if we should move to next phase
        if last_speaker and hasattr(last_speaker, 'name') and current_agent:
            # Only progress to the next agent if the current agent has finished speaking
            if last_speaker.name == current_agent.name if not isinstance(current_agent, list) else last_speaker.name in [agent.name for agent in current_agent]:
                # Save RE agent output when it finishes in the time stamped file.
                if last_speaker.name == "Requirement_Engineer" and self.workflow_controller.current_phase == "REQUIREMENTS":
                    try:
                        requirements_content = last_message
                        filepath = save_requirements_to_file(requirements_content)
                        print(f"Requirements saved to: {filepath}")
                    except Exception as e:
                        print(f"Error saving requirements: {e}")
                
                self.workflow_controller.update_phase(last_message)
                current_agent = self.workflow_controller.PHASES.get(self.workflow_controller.current_phase, None)
        
        if not current_agent:
            # Termination condition
            if "RATING" in last_message and int(last_message.split("RATING: ")[1][0]) > 7:
                return None  # End conversation
            return self.requirement_engineer  # Re-review if low rating form the critic
        
        # Handle parallel agents (tester and critic)
        if isinstance(current_agent, list):
            # Return the first agent in the parallel list, they will take turns
            return current_agent[0] if current_agent else None
        
        # Pass required context to next agent
        if current_agent.name == "Code_Translator":
            requirements = extract_value("Requirements:", group_chat.messages)
            current_agent.update_system_message(f"Input requirements: {requirements}")
        
        return current_agent
