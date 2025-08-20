from pathlib import Path
import matplotlib.pyplot as plt
import ast
import types
import unittest
import io

from ..services.agent_helpers import read_json_file
from ..services.result_evaluation import evaluate_codebleu_for_pairs, compute_and_print_codebleu_results, evaluate_time_logs
from ..services.output_validation import validate_python_syntax

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs'
GROUND_TRUTH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth.json'
GROUND_TRUTH_TEST = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth_test.json'

SINGLE_AGENT_CODE_OUT = OUTPUT_DIR / 'single_agent_results'/ 'generated_python_code.json'
DOUBLE_AGENT_CODE_OUT = OUTPUT_DIR / 'double_agent_results'/ 'generated_python_code.json'
MULTI_AGENT_CODE_OUT = OUTPUT_DIR / 'multi_agent_results'/ 'generated_python_code.json'
SINGLE_AGENT_TIME_OUT = OUTPUT_DIR / 'single_agent_results'/ 'time_log.json'
DOUBLE_AGENT_TIME_OUT = OUTPUT_DIR / 'double_agent_results'/ 'time_log.json'
MULTI_AGENT_TIME_OUT = OUTPUT_DIR / 'multi_agent_results'/ 'time_log.json'

def plot_codebleu_results(avg_score_single_agent, avg_score_double_agent, avg_score_multi_agent):
    """
    Plots the CodeBLEU results for single and double agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent', 'Multi Agent']
    scores = [avg_score_single_agent, avg_score_double_agent, avg_score_multi_agent]
    colors = ['#4F81BD', '#F28E2B', '#A5D86D']
    hatches = ['/', '\\', '|']

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, scores, color=colors, edgecolor='black', hatch=hatches, width=0.5)

    ax.set_ylabel('Average CodeBLEU Score', fontsize=12)
    ax.set_title('CodeBLEU Evaluation Results', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),  # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.figtext(0.99, 0.01, 'Source: Multi-agent LLMs SE Research Thesis', 
                horizontalalignment='right', fontsize=8, color='gray')
    plt.show()

def plot_time_log_results(avg_single_agent_time, avg_double_agent_time, avg_multi_agent_time):
    """
    Plots the time log results for single, double, and multi agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent', 'Multi Agent']
    scores = [avg_single_agent_time, avg_double_agent_time, avg_multi_agent_time]
    colors = ['#4F81BD', '#F28E2B', '#A5D86D']
    hatches = ['/', '\\', '|']

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, scores, color=colors, edgecolor='black', hatch=hatches, width=0.5)

    ax.set_ylabel('Average Time (seconds)', fontsize=12)
    ax.set_title('Time Log Evaluation Results', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(scores) * 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.figtext(0.99, 0.01, 'Source: Multi-agent LLMs SE Research Thesis',
                horizontalalignment='right', fontsize=8, color='gray')
    plt.show()

def compute_compile_ratio(output_codes):
    """
    Computes the compilation ratio for the translated code.
    """
    success_count = 0
    count = 0

    for key, translated_code in output_codes.items():
        result = validate_python_syntax(translated_code)
        if result.get("valid", True):
            success_count += 1
        count += 1

    return success_count / count if count > 0 else 0

def plot_compile_ratio_results(avg_single_agent_ratio, avg_double_agent_ratio, avg_multi_agent_ratio):
    """
    Plots the compilation ratio results for single, double, and multi agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent', 'Multi Agent']
    scores = [avg_single_agent_ratio, avg_double_agent_ratio, avg_multi_agent_ratio]
    colors = ['#4F81BD', '#F28E2B', '#A5D86D']
    hatches = ['/', '\\', '|']

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, scores, color=colors, edgecolor='black', hatch=hatches, width=0.5)

    ax.set_ylabel('Average Compilation Ratio', fontsize=12)
    ax.set_title('Compilation Ratio Evaluation Results', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.figtext(0.99, 0.01, 'Source: Multi-agent LLMs SE Research Thesis',
                horizontalalignment='right', fontsize=8, color='gray')
    plt.show()

def run_one_target(name: str, code_str: str, tests_str: str):
    """
    Run translated code + test code together, return CA score.
    """
    mod = types.ModuleType(f"sut_{name}")
    g = mod.__dict__
    g["__name__"] = f"sut_{name}"   # so unittest.main() inside code won't trigger

    # Execute code then tests in same namespace
    exec(code_str, g, g)
    exec(tests_str, g, g)

    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)

    total   = result.testsRun
    fails   = len(result.failures)
    errors  = len(result.errors)
    skipped = len(result.skipped)
    passed  = total - fails - errors - skipped
    ca      = (passed / total) if total else 0.0

    return {
        "tests_run": total,
        "passed": passed,
        "failures": fails,
        "errors": errors,
        "skipped": skipped,
        "ca_score": ca,
        "log": stream.getvalue(),
    }

def evaluate_CA(translated_codes: dict, ground_truth_tests: dict):
    """
    Run EVERY translated code against EVERY test set.
    Return overall average CA (across all runs).
    """
    results = {}
    ca_scores = []
    code_str = translated_codes.get("BalancedBrackets", "")
    tests_str = ground_truth_tests.get("BalancedBrackets", "")
    run_name = f"BalancedBrackets"
    print(f"Running {run_name}...")
    r = run_one_target(run_name, code_str, tests_str)
    ca_scores.append(r["ca_score"])
    # for code_key, code_str in list(translated_codes.items()):
    #     tests_str = ground_truth_tests.get(code_key, "")
    #     run_name = f"{code_key}"
    #     print(f"Running {run_name}...")
    #     r = run_one_target(run_name, code_str, tests_str)
    #     results[run_name] = r
    #     ca_scores.append(r["ca_score"])
    print(f"Finished running {run_name}. CA score: {r['ca_score']}")
    avg_ca = sum(ca_scores) / len(ca_scores) if ca_scores else 0.0
    return {"average_ca": avg_ca, "by_pair": results}

def main():
    """
    Main method to evaluate and plot CodeBLEU results for single and double agent setups.
    """
    # Evaluate CodeBLEU for single agent
    ground_truth = read_json_file(str(GROUND_TRUTH))
    ground_truth_test = read_json_file(str(GROUND_TRUTH_TEST))
    single_agent_code = read_json_file(str(SINGLE_AGENT_CODE_OUT))
    double_agent_code = read_json_file(str(DOUBLE_AGENT_CODE_OUT))
    multi_agent_code = read_json_file(str(MULTI_AGENT_CODE_OUT))

    # Evaluate CodeBLEU scores
    single_results = evaluate_codebleu_for_pairs(ground_truth, single_agent_code)
    double_results = evaluate_codebleu_for_pairs(ground_truth, double_agent_code)
    multi_results = evaluate_codebleu_for_pairs(ground_truth, multi_agent_code)

    avg_score_single_agent = compute_and_print_codebleu_results(single_results)
    avg_score_double_agent = compute_and_print_codebleu_results(double_results)
    avg_score_multi_agent = compute_and_print_codebleu_results(multi_results)

    # Compute time taken
    single_agent_time = read_json_file(str(SINGLE_AGENT_TIME_OUT))
    double_agent_time = read_json_file(str(DOUBLE_AGENT_TIME_OUT))
    multi_agent_time = read_json_file(str(MULTI_AGENT_TIME_OUT))

    avg_single_agent_time = evaluate_time_logs(single_agent_time)
    avg_double_agent_time = evaluate_time_logs(double_agent_time)
    avg_multi_agent_time = evaluate_time_logs(multi_agent_time)

    # Compute compilation ratios
    single_agent_compile_ratio = compute_compile_ratio(single_agent_code)
    double_agent_compile_ratio = compute_compile_ratio(double_agent_code)
    multi_agent_compile_ratio = compute_compile_ratio(multi_agent_code)

    # Run the output translated codes with the tests from the ground truth test
    ca_results = evaluate_CA(single_agent_code, ground_truth_test)

    # Plot results
    plot_codebleu_results(avg_score_single_agent, avg_score_double_agent, avg_score_multi_agent)
    plot_time_log_results(avg_single_agent_time, avg_double_agent_time, avg_multi_agent_time)
    plot_compile_ratio_results(single_agent_compile_ratio, double_agent_compile_ratio, multi_agent_compile_ratio)

if __name__ == "__main__":
    main()


