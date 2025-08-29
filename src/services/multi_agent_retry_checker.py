import re as _re
from typing import Dict

class RetryConditionChecker:
    """Service for handling different types of retry conditions"""
    
    @staticmethod
    def validation_check(workspace, condition: Dict) -> bool:
        """Check validation-specific retry condition"""
        validation_data = workspace.read(condition.get("workspace_key", "validation_results"))
        
        if not validation_data:
            return False
            
        validation_text = str(validation_data).lower()
        error_patterns = condition.get("error_patterns", [
            "syntax errors: none",
            "compilation issues: none", 
            "structural problems: none"
        ])
        
        # Check if any error pattern is NOT found (indicating an error)
        for pattern in error_patterns:
            if pattern.lower() not in validation_text:
                return True
                
        return False

    @staticmethod
    def critic_score_check(workspace, condition: Dict) -> bool:
        """Check critic score retry condition"""
        critic_data = workspace.read(condition.get("workspace_key", "critic_review"))
        
        if not critic_data:
            return False
            
        score = RetryConditionChecker._extract_critic_score(critic_data)
        min_score = condition.get("min_score", 7)
        
        return score is not None and score < min_score

    @staticmethod
    def tester_summary_check(workspace, condition: Dict) -> bool:
        """Check tester summary retry condition"""
        tester_data = workspace.read(condition.get("workspace_key", "test_results"))

        if not tester_data:
            return False

        tester_text = str(tester_data).lower()
    
        # Check for test failure indicators
        failure_patterns = condition.get("failure_patterns", ["fail", "error"])
    
        for pattern in failure_patterns:
            if pattern.lower() in tester_text:
                return True  # Indicates need to send to translator for retry
    
        return False

    @staticmethod
    def custom_check(workspace, condition: Dict) -> bool:
        """Handle custom retry logic"""
        custom_check = condition.get("check_function")
        if custom_check and callable(custom_check):
            return custom_check(workspace)
        return False

    @staticmethod
    def _extract_critic_score(critic_text):
        """Extract numeric score from critic text"""
        if not critic_text:
            return None
            
        score = None
        m_score = _re.search(r"Score\s*[:\-]?\s*(\d+)", str(critic_text), _re.IGNORECASE)
        if m_score:
            try:
                score = int(m_score.group(1))
            except Exception:
                score = None
        return score