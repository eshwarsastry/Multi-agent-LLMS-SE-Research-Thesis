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
