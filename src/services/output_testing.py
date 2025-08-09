import subprocess
import os
import tempfile
import time
import uuid
import shutil
import re
from typing import List, Dict

default_timeout = 10
TEST_NAME_CPP = re.compile(r"\b(?:void\s+)?(test_[A-Za-z0-9_]+)\s*\(")
TEST_NAME_PY  = re.compile(r"\bdef\s+(test_[A-Za-z0-9_]+)\s*\(")

# Try to find g++ on Windows
def find_gpp():
    """Find g++ compiler on Windows"""
    possible_paths = [
        "g++",  # If it's in PATH
        "C:\\MinGW\\bin\\g++.exe",
        "C:\\msys64\\mingw64\\bin\\g++.exe",
        "C:\\Program Files\\mingw-w64\\x86_64-8.1.0-posix-seh-rt_v6-rev0\\mingw64\\bin\\g++.exe",
        "C:\\Program Files (x86)\\mingw-w64\\x86_64-8.1.0-posix-seh-rt_v6-rev0\\mingw64\\bin\\g++.exe",
    ]
    
    for path in possible_paths:
        if shutil.which(path) is not None:
            print(f" Found g++ at: {path}")
            return path
    
    print(" g++ not found. Please install MinGW or add g++ to PATH")
    return None

# Get the g++ path
GPP_PATH = find_gpp()

def _execute_command(command, input_data=""):
    """
    Executes a shell command and captures its output.
    This is a helper function used by both run_cpp_code and run_python_code.
    """
    stdout = ""
    stderr = ""
    returncode = None
    success = False
    
    # Add execution ID for tracking
    execution_id = str(uuid.uuid4())[:8]
    print(f"\n [EXECUTION {execution_id}] Starting command execution...")
    print(f" Command: {' '.join(command)}")
    print(f" Input: {repr(input_data)}")
    
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        stdout, stderr = process.communicate(input=input_data, timeout=default_timeout)
        returncode = process.returncode
        success = (returncode == 0)
        
        execution_time = time.time() - start_time
        print(f"  Execution time: {execution_time:.2f} seconds")
        print(f" Output: {repr(stdout)}")
        print(f" Errors: {repr(stderr)}")
        print(f" Return code: {returncode}")
        print(f" Success: {success}")

    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        stderr = f"TimeoutExpired: Command took too long to execute ({default_timeout} seconds).\n" + stderr
        returncode = -1
        print(f" TIMEOUT: Command exceeded {default_timeout} seconds")
    except FileNotFoundError:
        stderr = f"Error: Command not found or executable missing: {' '.join(command)}\n"
        returncode = 127
        print(f" FILE NOT FOUND: {' '.join(command)}")
    except Exception as e:
        stderr = f"An unexpected error occurred: {e}\n" + stderr
        returncode = -2
        print(f" UNEXPECTED ERROR: {e}")

    print(f"🔍 [EXECUTION {execution_id}] Completed\n")
    return stdout.strip(), stderr.strip(), returncode, success

def run_cpp_code(code_string: str, input_data: str = "") -> dict:
    """
    Compiles and runs C++ code.
    The Tester_Agent will call this function.
    """
    print(f"\n [C++ EXECUTION] Starting C++ code execution...")
    print(f" Code length: {len(code_string)} characters")
    print(f" Input data: {repr(input_data)}")
    
    if GPP_PATH is None:
        error_msg = "g++ compiler not found. Please install MinGW or add g++ to PATH"
        print(f" {error_msg}")
        return {
            "stdout": "",
            "stderr": error_msg,
            "returncode": -1,
            "success": False,
            "log": error_msg
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cpp_file = os.path.join(tmpdir, "program.cpp")
        executable_file = os.path.join(tmpdir, "program")
        if os.name == "nt":
            executable_file += ".exe"

        log = []
        full_success = True

        try:
            with open(cpp_file, "w", encoding='utf-8') as f:
                f.write(code_string)
            log.append(f"C++ code written to {cpp_file}")
            print(f" C++ code saved to: {cpp_file}")
        except Exception as e:
            print(f" Failed to write C++ file: {e}")
            return {
                "stdout": "",
                "stderr": f"Failed to write C++ file: {e}",
                "returncode": -1,
                "success": False,
                "log": "\n".join(log)
            }

        compile_command = [GPP_PATH, cpp_file, "-o", executable_file]
        log.append(f"Compiling with command: {' '.join(compile_command)}")
        print(f" Compiling C++ code with {GPP_PATH}...")
        compile_stdout, compile_stderr, compile_returncode, compile_success = \
            _execute_command(compile_command)

        if not compile_success:
            full_success = False
            log.append(f"Compilation Failed (Return Code: {compile_returncode}):")
            if compile_stdout: log.append(f"Compile STDOUT:\n{compile_stdout}")
            if compile_stderr: log.append(f"Compile STDERR:\n{compile_stderr}")
            print(f" C++ compilation failed!")
            return {
                "stdout": "",
                "stderr": f"Compilation failed.\n{compile_stderr}",
                "returncode": compile_returncode,
                "success": False,
                "log": "\n".join(log)
            }
        log.append("Compilation Successful.")
        print(f" C++ compilation successful!")

        execute_command = [executable_file]
        log.append(f"Executing with command: {' '.join(execute_command)}")
        print(f"  Running C++ executable...")
        run_stdout, run_stderr, run_returncode, run_success = \
            _execute_command(execute_command, input_data=input_data)

        if not run_success:
            full_success = False
            log.append(f"Execution Failed (Return Code: {run_returncode}):")
            if run_stdout: log.append(f"Run STDOUT:\n{run_stdout}")
            if run_stderr: log.append(f"Run STDERR:\n{run_stderr}")
            print(f" C++ execution failed!")
        else:
            log.append("Execution Successful.")
            print(f" C++ execution successful!")

        result = {
            "stdout": run_stdout,
            "stderr": run_stderr,
            "returncode": run_returncode,
            "success": full_success and run_success,
            "log": "\n".join(log)
        }
        
        print(f" C++ Result: {result}")
        return result

def run_python_code(code_string: str, input_data: str = "") -> dict:
    """
    Runs Python code.
    The Tester_Agent will call this function.
    """
    print(f"\n [PYTHON EXECUTION] Starting Python code execution...")
    print(f" Code length: {len(code_string)} characters")
    print(f" Input data: {repr(input_data)}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "program.py")

        log = []
        full_success = True

        try:
            with open(py_file, "w", encoding='utf-8') as f:
                f.write(code_string)
            log.append(f"Python code written to {py_file}")
            print(f" Python code saved to: {py_file}")
        except Exception as e:
            print(f" Failed to write Python file: {e}")
            return {
                "stdout": "",
                "stderr": f"Failed to write Python file: {e}",
                "returncode": -1,
                "success": False,
                "log": "\n".join(log)
            }

        execute_command = ["python3", py_file]
        log.append(f"Executing with command: {' '.join(execute_command)}")
        print(f" Running Python code...")
        run_stdout, run_stderr, run_returncode, run_success = \
            _execute_command(execute_command, input_data=input_data)

        if not run_success:
            full_success = False
            log.append(f"Execution Failed (Return Code: {run_returncode}):")
            if run_stdout: log.append(f"Run STDOUT:\n{run_stdout}")
            if run_stderr: log.append(f"Run STDERR:\n{run_stderr}")
            print(f" Python execution failed!")
        else:
            log.append("Execution Successful.")
            print(f" Python execution successful!")

        result = {
            "stdout": run_stdout,
            "stderr": run_stderr,
            "returncode": run_returncode,
            "success": full_success and run_success,
            "log": "\n".join(log)
        }
        
        print(f" Python Result: {result}")
        return result

def extract_cpp_test_names(cpp_tests: str) -> List[str]:
    return TEST_NAME_CPP.findall(cpp_tests or "")

def extract_python_test_names(py_tests: str) -> List[str]:
    return TEST_NAME_PY.findall(py_tests or "")

def run_and_compare_tests(
    legacy_code: str,
    translated_code: str,
    cpp_tests: str,
    py_tests: str,
) -> Dict:
    """
    Runtime test harness:
    - Appends a single test at a time to each program
    - Runs C++ and Python separately
    - Compares outputs and errors
    Returns: {
        "total": int, "passed": int, "failed": int, "success_rate": float,
        "match": bool,
        "details": [
           {"name": str, "cpp_ok": bool, "py_ok": bool,
            "cpp_stdout": str, "py_stdout": str,
            "cpp_stderr": str, "py_stderr": str,
            "passed": bool}
        ]
    }
    """
    cpp_names = extract_cpp_test_names(cpp_tests)
    py_names  = extract_python_test_names(py_tests)

    # Require 1:1 matching names
    common = [n for n in cpp_names if n in py_names]
 
    results = []
    passed_count = 0

    for name in common:
        # Build per-test C++ program: original + tests + driver main that calls the one test
        cpp_driver = f"""
int main() {{
    {name}();
    return 0;
}}
"""
        cpp_full = "\n".join([legacy_code, cpp_tests, cpp_driver])

        cpp_res = run_cpp_code(cpp_full)  # expects dict with stdout/stderr/success/returncode/log
        cpp_ok = cpp_res.get("success", False) and cpp_res.get("returncode", 1) == 0

        # Build per-test Python script: translated + tests + call the one test
        py_driver = f"""
if __name__ == "__main__":
    {name}()
"""
        py_full = "\n".join([translated_code, py_tests, py_driver])

        py_res = run_python_code(py_full)  # expects dict with stdout/stderr/success/returncode/log
        py_ok = py_res.get("success", False) and py_res.get("returncode", 1) == 0

        # Compare success + stdout exactly (when both ran)
        outputs_match = (
            cpp_ok and py_ok and
            (cpp_res.get("stdout","").strip() == py_res.get("stdout","").strip())
        )
        passed = outputs_match

        results.append({
            "name": name,
            "cpp_ok": cpp_ok,
            "py_ok": py_ok,
            "cpp_stdout": (cpp_res.get("stdout","") or "").strip(),
            "py_stdout": (py_res.get("stdout","") or "").strip(),
            "cpp_stderr": (cpp_res.get("stderr","") or "").strip(),
            "py_stderr": (py_res.get("stderr","") or "").strip(),
            "passed": passed,
        })

        if passed:
            passed_count += 1

    total = len(common)
    summary = {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "success_rate": (100.0 * passed_count / total) if total else 0.0,
        "match": passed_count == total,
        "details": results,
    }
    return summary
    

