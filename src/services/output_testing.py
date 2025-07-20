import subprocess
import os
import tempfile

default_timeout = 10

def _execute_command(command, input_data=""):
    """
    Executes a shell command and captures its output.
    This is a helper function used by both run_cpp_code and run_python_code.
    """
    stdout = ""
    stderr = ""
    returncode = None
    success = False
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

    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        stderr = f"TimeoutExpired: Command took too long to execute ({default_timeout} seconds).\n" + stderr
        returncode = -1
    except FileNotFoundError:
        stderr = f"Error: Command not found or executable missing: {' '.join(command)}\n"
        returncode = 127
    except Exception as e:
        stderr = f"An unexpected error occurred: {e}\n" + stderr
        returncode = -2

    return stdout.strip(), stderr.strip(), returncode, success

def run_cpp_code(code_string: str, input_data: str) -> dict:
    """
    Compiles and runs C++ code.
    The Tester_Agent will call this function.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cpp_file = os.path.join(tmpdir, "program.cpp")
        executable_file = os.path.join(tmpdir, "program")

        log = []
        full_success = True

        try:
            with open(cpp_file, "w", encoding='utf-8') as f:
                f.write(code_string)
            log.append(f"C++ code written to {cpp_file}")
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Failed to write C++ file: {e}",
                "returncode": -1,
                "success": False,
                "log": "\n".join(log)
            }

        compile_command = ["g++", cpp_file, "-o", executable_file]
        log.append(f"Compiling with command: {' '.join(compile_command)}")
        compile_stdout, compile_stderr, compile_returncode, compile_success = \
            _execute_command(compile_command, timeout=default_timeout)

        if not compile_success:
            full_success = False
            log.append(f"Compilation Failed (Return Code: {compile_returncode}):")
            if compile_stdout: log.append(f"Compile STDOUT:\n{compile_stdout}")
            if compile_stderr: log.append(f"Compile STDERR:\n{compile_stderr}")
            return {
                "stdout": "",
                "stderr": f"Compilation failed.\n{compile_stderr}",
                "returncode": compile_returncode,
                "success": False,
                "log": "\n".join(log)
            }
        log.append("Compilation Successful.")

        execute_command = [executable_file]
        log.append(f"Executing with command: {' '.join(execute_command)}")
        run_stdout, run_stderr, run_returncode, run_success = \
            _execute_command(execute_command, input_data=input_data, timeout=default_timeout)

        if not run_success:
            full_success = False
            log.append(f"Execution Failed (Return Code: {run_returncode}):")
            if run_stdout: log.append(f"Run STDOUT:\n{run_stdout}")
            if run_stderr: log.append(f"Run STDERR:\n{run_stderr}")
        else:
            log.append("Execution Successful.")

        return {
            "stdout": run_stdout,
            "stderr": run_stderr,
            "returncode": run_returncode,
            "success": full_success and run_success,
            "log": "\n".join(log)
        }


def run_python_code(code_string: str, input_data: str) -> dict:
    """
    Runs Python code.
    The Tester_Agent will call this function.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "program.py")

        log = []
        full_success = True

        try:
            with open(py_file, "w", encoding='utf-8') as f:
                f.write(code_string)
            log.append(f"Python code written to {py_file}")
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Failed to write Python file: {e}",
                "returncode": -1,
                "success": False,
                "log": "\n".join(log)
            }

        execute_command = ["python3", py_file]
        log.append(f"Executing with command: {' '.join(execute_command)}")
        run_stdout, run_stderr, run_returncode, run_success = \
            _execute_command(execute_command, input_data=input_data, timeout=default_timeout)

        if not run_success:
            full_success = False
            log.append(f"Execution Failed (Return Code: {run_returncode}):")
            if run_stdout: log.append(f"Run STDOUT:\n{run_stdout}")
            if run_stderr: log.append(f"Run STDERR:\n{run_stderr}")
        else:
            log.append("Execution Successful.")

        return {
            "stdout": run_stdout,
            "stderr": run_stderr,
            "returncode": run_returncode,
            "success": full_success and run_success,
            "log": "\n".join(log)
        }