import ast
import os
import tempfile

from .output_testing import _execute_command, find_gpp

GPP_PATH = find_gpp()


def validate_python_syntax(code_string: str) -> dict:
    """
    Validates Python code syntax.
    The Validator_Agent will call this function.
    """
    print(f"\n [PYTHON SYNTAX VALIDATION] Validating Python syntax...")
    print(f" Code length: {len(code_string)} characters")
    
    try:
        # Parse the code to check for syntax errors
        ast.parse(code_string)
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


def validate_cpp_syntax(code_string: str) -> dict:
    """
    Validates C++ code syntax and compilation.
    The Validator_Agent will call this function.
    """
    print(f"\n [C++ SYNTAX VALIDATION] Validating C++ syntax...")
    print(f" Code length: {len(code_string)} characters")
    
    if GPP_PATH is None:
        error_msg = "g++ compiler not found. Please install MinGW or add g++ to PATH"
        print(f" {error_msg}")
        return {
            "valid": False,
            "errors": [error_msg],
            "message": error_msg
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cpp_file = os.path.join(tmpdir, "program.cpp")
        
        try:
            with open(cpp_file, "w", encoding='utf-8') as f:
                f.write(code_string)
            print(f" C++ code saved to: {cpp_file}")
        except Exception as e:
            print(f" Failed to write C++ file: {e}")
            return {
                "valid": False,
                "errors": [f"Failed to write C++ file: {e}"],
                "message": f"File write error: {e}"
            }

        compile_command = [GPP_PATH, "-fsyntax-only", cpp_file]
        print(f" Checking C++ syntax with {GPP_PATH}...")
        compile_stdout, compile_stderr, compile_returncode, compile_success = \
            _execute_command(compile_command)

        if compile_success:
            print(f" C++ syntax is valid!")
            return {
                "valid": True,
                "errors": [],
                "message": "C++ syntax is valid"
            }
        else:
            print(f" C++ syntax error!")
            return {
                "valid": False,
                "errors": [compile_stderr] if compile_stderr else ["Compilation failed"],
                "message": "C++ syntax error"
            }