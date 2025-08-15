from services.agent_workflow import WorkflowController


class SpeakerSelector:
    
    def __init__(self, controller: WorkflowController):
        self.controller = controller
        self._order = controller.get_current_agent_names()
        self._i = 0

    def next_speaker(self) -> str:
        if self._i >= len(self._order):
            return None
        name = self._order[self._i]
        self._i += 1
        return name