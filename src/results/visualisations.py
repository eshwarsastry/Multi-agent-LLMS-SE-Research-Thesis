from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from ..services.agent_helpers import read_json_file
from ..services.result_evaluation import evaluate_codebleu_for_pairs, compute_and_print_codebleu_results, evaluate_time_logs
from ..services.output_validation import validate_python_syntax

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs'
GROUND_TRUTH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth.json'

SINGLE_AGENT_CODE_OUT = OUTPUT_DIR / 'single_agent_results'/ 'generated_python_code.json'
DOUBLE_AGENT_CODE_OUT = OUTPUT_DIR / 'double_agent_results'/ 'generated_python_code.json'
SINGLE_AGENT_TIME_OUT = OUTPUT_DIR / 'single_agent_results'/ 'time_log.json'
DOUBLE_AGENT_TIME_OUT = OUTPUT_DIR / 'double_agent_results'/ 'time_log.json'

def plot_codebleu_results(avg_score_single_agent, avg_score_double_agent):
    """
    Plots the CodeBLEU results for single and double agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent']
    scores = [avg_score_single_agent, avg_score_double_agent]
    colors = ['#4F81BD', '#F28E2B']
    hatches = ['/', '\\']

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

def plot_time_log_results(avg_single_agent_time, avg_double_agent_time):
    """
    Plots the time log results for single and double agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent']
    scores = [avg_single_agent_time, avg_double_agent_time]
    colors = ['#4F81BD', '#F28E2B']
    hatches = ['/', '\\']

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

def plot_compile_ratio_results(avg_single_agent_ratio, avg_double_agent_ratio):
    """
    Plots the compilation ratio results for single and double agent evaluations.
    Enhanced with value labels, grid, and style.
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = ['Single Agent', 'Double Agent']
    scores = [avg_single_agent_ratio, avg_double_agent_ratio]
    colors = ['#4F81BD', '#F28E2B']
    hatches = ['/', '\\']

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

def main():
    """
    Main method to evaluate and plot CodeBLEU results for single and double agent setups.
    """
    # Evaluate CodeBLEU for single agent
    ground_truth = read_json_file(str(GROUND_TRUTH))
    single_agent_code = read_json_file(str(SINGLE_AGENT_CODE_OUT))
    double_agent_code = read_json_file(str(DOUBLE_AGENT_CODE_OUT))

    # Evaluate CodeBLEU scores
    single_results = evaluate_codebleu_for_pairs(ground_truth, single_agent_code)
    double_results = evaluate_codebleu_for_pairs(ground_truth, double_agent_code)

    avg_score_single_agent = compute_and_print_codebleu_results(single_results)
    avg_score_double_agent = compute_and_print_codebleu_results(double_results)

    # Compute time taken
    single_agent_time = read_json_file(str(SINGLE_AGENT_TIME_OUT))
    double_agent_time = read_json_file(str(DOUBLE_AGENT_TIME_OUT))

    avg_single_agent_time = evaluate_time_logs(single_agent_time)
    avg_double_agent_time = evaluate_time_logs(double_agent_time)

    # Compute compilation ratios
    single_agent_compile_ratio = compute_compile_ratio(single_agent_code)
    double_agent_compile_ratio = compute_compile_ratio(double_agent_code)

    # Plot results
    plot_codebleu_results(avg_score_single_agent, avg_score_double_agent)
    plot_time_log_results(avg_single_agent_time, avg_double_agent_time)
    plot_compile_ratio_results(single_agent_compile_ratio, double_agent_compile_ratio)

if __name__ == "__main__":
    main()


