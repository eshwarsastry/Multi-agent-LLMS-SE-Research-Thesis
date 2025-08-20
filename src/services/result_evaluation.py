from codebleu import calc_codebleu

def evaluate_codebleu_for_pairs(ground_truth, generated_code, lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None):
	"""
	For each key present in both ground_truth and generated_code, evaluates CodeBLEU and returns a dict of results.
	"""
	results = {}
	for key in generated_code:
		if key in ground_truth:
			reference = ground_truth[key]
			prediction = generated_code[key]
			score = calc_codebleu([reference], [prediction], lang=lang, weights=weights, tokenizer=tokenizer)
			results[key] = score
	return results

def compute_and_print_codebleu_results(results):
	"""
	Prints CodeBLEU results for each key and the average CodeBLEU value.
	"""
	total_score = 0
	count = 0
	for key, score_dict in results.items():
		codebleu_score = score_dict.get('codebleu', score_dict if isinstance(score_dict, float) else None)
		if codebleu_score is not None:
			total_score += codebleu_score
			count += 1
	avg_score = total_score / count if count > 0 else 0
	return avg_score

def evaluate_time_logs(time_logs):
	"""
	Evaluates and compares time logs for the given 2 agent frameworks to compare.
	"""
	total_time = 0
	count = 0
	for key, time_value in time_logs.items():
		print(f"{key}: Time = {time_value}")
		total_time += time_value
		count += 1
	avg_time = total_time / count if count > 0 else 0
	return avg_time
