import os
from pathlib import Path
from typing import Dict

from ..services.agent_helpers import read_json_file, save_output_to_json_file
from ..services.result_evaluation import evaluate_codebleu_for_pairs, print_codebleu_results
from .multi_agent_workflow import create_custom_workflow

# Output paths (separate folder for custom sequential flow)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'outputs' / 'multi_agent_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CODE_OUT = OUTPUT_DIR / 'generated_python_code.json'
REQ_OUT = OUTPUT_DIR / 'generated_requirements.json'
VALID_OUT = OUTPUT_DIR / 'generated_validator.json'
TEST_OUT = OUTPUT_DIR / 'generated_tests.json'
CRITIC_OUT = OUTPUT_DIR / 'generated_critic.json'

INPUT_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'input_program.json'
GROUND_TRUTH_PATH = Path(__file__).resolve().parent.parent / 'inputs' / 'ground_truth.json'


def main(max_items: int | None = None):
    # Orchestration-owned phase->speakers mapping
    phase_speakers = {
        "REQUIREMENTS": ["Requirement_Engineer"],
        "TRANSLATION": ["Code_Translator"],
        "VALIDATION": ["Code_Validator"],
        "TESTING": ["Code_Tester"],
        "REVIEW": ["Critic"],
        "COMPLETE": [],
    }

    # Patterns to extract final outputs from the combined chat history
    agent_patterns = {
        "Requirement_Engineer": r"Title:\s*.*",
        "Code_Translator": r"```(python|py|python3)\n(.*?)```",
        "Code_Validator": r"(Validation Summary:?\s*.*)",
        "Code_Tester": r"(Test Summary:?\s*.*)",
        "Critic": r"(Score:?\s*\d+|Critique:?\s*.*|Suggestions?:?\s*.*)",
    }

    agents, run = create_custom_workflow(phase_speakers=phase_speakers,
                                         phase_order= ["REQUIREMENTS", "TRANSLATION", "VALIDATION", "TESTING", "REVIEW", "COMPLETE"],
                                         agent_patterns=agent_patterns)

    input_cpp_codes: Dict[str, str] = read_json_file(str(INPUT_PATH))

    translations: Dict[str, str] = {}
    requirements: Dict[str, str] = {}
    validations: Dict[str, str] = {}
    tests: Dict[str, str] = {}
    critic_reviews: Dict[str, str] = {}


    items = list(input_cpp_codes.items())[:2]
    if max_items is not None:
        items = items[:max_items]

    for key, cpp_code in items:
        print(f"Translating C++ code for key: {key}")
        chat_history, outputs = run(cpp_code)

        # Collect outputs
        if outputs.get('translated_code'):
            translations[key] = outputs['translated_code']
        if outputs.get('requirements'):
            requirements[key] = outputs['requirements']
        if outputs.get('validation_results'):
            validations[key] = outputs['validation_results']
        if outputs.get('test_results'):
            tests[key] = outputs['test_results']
        if outputs.get('critic_review'):
            critic_reviews[key] = outputs['critic_review']

        # Persist after each item (safer on long runs)
        save_output_to_json_file(str(CODE_OUT), translations)
        save_output_to_json_file(str(REQ_OUT), requirements)
        save_output_to_json_file(str(VALID_OUT), validations)
        save_output_to_json_file(str(TEST_OUT), tests)
        save_output_to_json_file(str(CRITIC_OUT), critic_reviews)

    # Evaluate CodeBLEU if ground truth exists
    if GROUND_TRUTH_PATH.exists():
        ground_truth = read_json_file(str(GROUND_TRUTH_PATH))
        generated_code = read_json_file(str(CODE_OUT)) if CODE_OUT.exists() else {}
        results = evaluate_codebleu_for_pairs(ground_truth, generated_code, lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)
        print_codebleu_results(results)
    else:
        print(f"Ground truth not found at {GROUND_TRUTH_PATH}")


if __name__ == '__main__':
    # Limit items for a first run if desired, e.g., main(max_items=1)
    main()
