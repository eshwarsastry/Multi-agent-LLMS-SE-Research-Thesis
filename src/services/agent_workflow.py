import re


class WorkflowController:
    def __init__(self, phases, phase_order):
        self.PHASES = phases
        self.PHASE_ORDER = phase_order
        self.current_phase = phase_order[0]
        self.phase_history = []

    def _should_retry(self, phase, last_message):
        """Check if last_message triggers retry based on phase's retry_on rules."""
        retry_triggers = self.PHASES[phase]["retry_on"]
        for trigger in retry_triggers:
            if isinstance(last_message, dict):
                # Direct dict key check
                if trigger in last_message.get("error_type", ""):
                    return True
            elif isinstance(last_message, str):
                if re.search(trigger, last_message, re.IGNORECASE):
                    return True
        return False

    def next_phase(self, last_message):
        # Retry logic
        if self._should_retry(self.current_phase, last_message):
            return "TRANSLATION"

        # Move forward in sequence
        current_idx = self.PHASE_ORDER.index(self.current_phase)
        if current_idx < len(self.PHASE_ORDER) - 1:
            return self.PHASE_ORDER[current_idx + 1]
        return "COMPLETE"

    def update_phase(self, last_message):
        new_phase = self.next_phase(last_message)
        if new_phase != self.current_phase:
            self.phase_history.append(self.current_phase)
            self.current_phase = new_phase
        return self.PHASES.get(self.current_phase, {}).get("agents", [])