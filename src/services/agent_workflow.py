from typing import Dict, List

class WorkflowController:

    def __init__(
        self,
        phase_speakers: Dict[str, List[str]] | None = None,
        phase_order: List[str] | None = None,
    ):

        self.phase_speakers: Dict[str, List[str]] = phase_speakers or {}

        self.phase_order: List[str] = phase_order or list(self.phase_speakers.keys())
        self.current_phase = self.phase_order[0] if self.phase_order else "COMPLETE"

    def next_phase(self) -> str:
        if self.current_phase not in self.phase_order:
            self.current_phase = self.phase_order[0] if self.phase_order else "COMPLETE"
            return self.current_phase
        idx = self.phase_order.index(self.current_phase)
        self.current_phase = (
            self.phase_order[idx + 1] if idx < len(self.phase_order) - 1 else "COMPLETE"
        )
        return self.current_phase

    def set_phase_speakers(self, mapping: Dict[str, List[str]]):

        self.phase_speakers.update(mapping)

    def get_speakers_for_phase(self, phase: str) -> List[str]:
        return list(self.phase_speakers.get(phase, []))

    def current_phase_speakers(self) -> List[str]:
        return self.get_speakers_for_phase(self.current_phase)

    def get_current_agent_names(self) -> List[str]:
        
        ordered: List[str] = []
        for ph in self.phase_order:
            for name in self.get_speakers_for_phase(ph):
                if name not in ordered:
                    ordered.append(name)
        return ordered