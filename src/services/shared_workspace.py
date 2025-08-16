from typing import Dict, List, Any, Optional

class SharedWorkspace:
    """Shared data space for multi-agent communication"""
    
    def __init__(self, workspace_id: str = "default", agent_access_patterns: Dict[str, List[str]] = None):
        self.workspace_id = workspace_id
        self.data: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.agent_access_patterns = agent_access_patterns or {}
        
    def write(self, key: str, value: Any, agent_name: str) -> None:
        """Write data to workspace with agent attribution"""
        self.data[key] = {
            "value": value,
            "agent": agent_name,
            "timestamp": self._get_timestamp()
        }
        self.history.append({
            "action": "write",
            "key": key,
            "agent": agent_name,
            "timestamp": self._get_timestamp()
        })
    
    def read(self, key: str) -> Optional[Any]:
        """Read data from workspace"""
        return self.data.get(key, {}).get("value")
    
    def get_context_for_agent(self, agent_name: str, relevant_keys: List[str] = None) -> Dict[str, Any]:
        """Get relevant context for a specific agent"""
        # Get values by specific keys.
        if relevant_keys:
            return {k: self.data[k]["value"] for k in relevant_keys if k in self.data}
        
        # Else, use agent-specific access pattern from orchestration layer
        allowed_keys = self.agent_access_patterns.get(agent_name, list(self.data.keys()))
        
        # User_Proxy can access everything by default
        if agent_name == "User_Proxy" and agent_name not in self.agent_access_patterns:
            allowed_keys = list(self.data.keys())
        
        return {k: self.data[k]["value"] for k in allowed_keys if k in self.data}
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """Get all agent outputs"""
        return {k: v["value"] for k, v in self.data.items()}
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()