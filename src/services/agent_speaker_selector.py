from .agent_helpers import extract_value

class SpeakerSelector:
    def __init__(self, workflow_controller, requirement_engineer):
        self.workflow_controller = workflow_controller
        self.requirement_engineer = requirement_engineer
        self.parallel_index = {}  # Tracks which agent in a parallel phase spoke last

    def _is_current_agent_done(self, last_speaker, current_agents):
        """Check if the last speaker is part of the current phase."""
        return last_speaker.name in [a.name for a in current_agents]

    def _get_next_parallel_agent(self, phase_name, current_agents, last_speaker):
        """Rotate between parallel agents for this phase."""
        if phase_name not in self.parallel_index:
            self.parallel_index[phase_name] = 0

        if last_speaker and self._is_current_agent_done(last_speaker, current_agents):
            idx = [a.name for a in current_agents].index(last_speaker.name)
            next_idx = (idx + 1) % len(current_agents)
            self.parallel_index[phase_name] = next_idx

        return current_agents[self.parallel_index[phase_name]]

    def select_speaker(self, last_speaker, group_chat):
        last_message = group_chat.messages[-1]["content"] if group_chat.messages else ""

        current_agents = self.workflow_controller.PHASES.get(self.workflow_controller.current_phase, {}).get("agents", [])

        # Advance phase if current agent is done
        if last_speaker and current_agents and self._is_current_agent_done(last_speaker, current_agents):
            current_agents = self.workflow_controller.update_phase(last_message)

        # If workflow is complete
        if not current_agents:
            return None

        # Handle parallel agents
        if len(current_agents) > 1:
            return self._get_next_parallel_agent(self.workflow_controller.current_phase, current_agents, last_speaker)

        # Inject requirements into translator phase
        if current_agents[0].name == "Code_Translator":
            requirements = extract_value("Requirements:", group_chat.messages)
            current_agents[0].update_system_message(f"Input requirements: {requirements}")

        return current_agents[0]
