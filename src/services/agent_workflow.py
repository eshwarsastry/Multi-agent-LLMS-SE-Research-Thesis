
class WorkflowController:
    def __init__(self, phases):
        self.PHASES = phases
        self.current_phase = "REQUIREMENTS"
        self.phase_history = []
        
    def next_phase(self, last_message):
        phase_order = list(self.PHASES.keys())
        current_idx = phase_order.index(self.current_phase)
        
        # Handle validation failures
        if self.current_phase == "PARALLEL" and "errors" in last_message:
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
