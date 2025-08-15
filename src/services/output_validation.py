import ast
import os
import tempfile
from typing import Dict
from typing_extensions import Annotated

from .output_testing import  find_gpp

GPP_PATH = find_gpp()


def validate_python_syntax(
    translated_code: str
) -> Dict:
    """ 
    Validate the translated Python code to check if it compiles.
    """

    print(f"\n [PYTHON SYNTAX VALIDATION] Validating Python syntax...")
    print(f" Code length: {len(translated_code)} characters")

    try:
        # Parse the code to check for syntax errors
        ast.parse(translated_code)
        print(f" Python syntax is valid!")
        return {
            "valid": True,
            "errors": [],
            "message": "Python syntax is valid"
        }
    except SyntaxError as e:
        print(f" Python syntax error: {e.msg} at line {e.lineno}")
        return {
            "valid": False,
            "errors": [f"SyntaxError: {e.msg} at line {e.lineno}"],
            "message": f"Python syntax error: {e.msg}"
        }
    except Exception as e:
        print(f" Unexpected error: {str(e)}")
        return {
            "valid": False,
            "errors": [f"Error: {str(e)}"],
            "message": f"Unexpected error: {str(e)}"
        }
