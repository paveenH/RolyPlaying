#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 11:43:55 2024

@author: paveenhuang
"""

import json
import argparse
import os
from tqdm import tqdm

from vicuna import VicundaModel

# Define the path to the JSON files
PATH = "/data2/paveen/RolePlaying/src/models/components/mmlu"

# Parse combined arguments
parser = argparse.ArgumentParser(description="Run VicundaModel on a specific task.")
parser.add_argument("task_size", type=str, help="The task and size as a combined argument.")
args = parser.parse_args()

# Split task and size
task, size = args.task_size.split()

# Define model path
model_path = f"/data2/paveen/RolePlaying/shared/llama3/{size}"

# Define JSON file path
json_path = os.path.join(PATH, f"{task}.json")

# Define save directory for answers
save_dir = os.path.join("/data2/paveen/RolePlaying/src/models/components/answer_honest")
os.makedirs(save_dir, exist_ok=True)

# Initialize VicundaModel
vc = VicundaModel(model_path=model_path)
template = vc.template

# Define the template for generating answers
# ABCD without honest
# template = "Would you answer the following question with A, B, C or D?\nQuestion: {context}\nNow you are a {character} expert, your answer among{{A, B, C, D}} is: "
# ABCDE without honest
# template = "Would you answer the following question with A, B, C, D or E?\nQuestion: {context}\nE) I am not sure.\nNow you are a {character} expert, your answer among{{A, B, C, D, E}} is: "
# # ABCDEn with honest

# # Original
# template = "You are a {character}, You are a {character}, You are a {character}, would you answer the following question with A, B, C or D? \n Question: {context}\n Answer: "

# Define the list of characters
task_name = task.replace('_', ' ')
characters = [f"none {task_name}", task_name]

# Load JSON data
print(f"Loading JSON data from {json_path}")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total samples loaded: {len(data)}")

# Initialize storage for generated answers
# generated_answers_storage = {character: [] for character in characters}

# Initialize accuracy tracking
# accuracy_counts = {character: {"correct": 0, "total": 0} for character in characters}
accuracy_counts = {character: {"correct": 0, 
                               "total": 0, 
                               "E_count": 0,
                               "invalid": 0} 
                   for character in characters}

label_mapping = ["A", "B", "C", "D"]

print("Starting answer generation and accuracy calculation...")
for idx, sample in enumerate(tqdm(data, desc="Processing Samples")):
    context = sample.get("text", "")
    true_label_int = sample.get("label", -1)   # Ensure label is uppercase and stripped
    true_label = label_mapping[true_label_int]

    for character in characters:
        # Generate prompt
        prompt = template.format(character=character, context=context)

        # Generate answer using vc.generate
        generated_output = vc.generate([prompt])[0]  # Get the single output
        generated_answer = generated_output.strip().upper()
        answer_key = f"answer_{character.replace(' ', '_')}"
        sample[answer_key] = generated_answer
        
        # Increase total count. We want to count all possible outputs (valid or not).
        accuracy_counts[character]["total"] += 1
        
        # Check the answer
        if generated_answer in ["A", "B", "C", "D"]:
            # Compare with ground truth
            if generated_answer == true_label:
                accuracy_counts[character]["correct"] += 1

        elif generated_answer == "E":
            # E is uncertain, do not count for accuracy, but increment E_count
            accuracy_counts[character]["E_count"] += 1

        else:
            accuracy_counts[character]["invalid"] += 1
            print(f"Sample {idx}, Character '{character}': Invalid generated answer '{generated_answer}'")        

# After processing all samples, compute accuracy
accuracy_results = {}
for character in characters:
    correct = accuracy_counts[character]["correct"]
    total = accuracy_counts[character]["total"]
    E_count = accuracy_counts[character]["E_count"]
    invalid = accuracy_counts[character]["invalid"]
    accuracy = (correct / total) * 100 if total > 0 else 0.0
    accuracy_results[character] = {
        "correct": correct,
        "total": total,
        "E_count": E_count,
        "invalid": invalid,
        "accuracy_percentage": round(accuracy, 2)
    }
    print(f"Accuracy for {character}: {accuracy_results[character]['accuracy_percentage']}% ({correct}/{total})")
    print(f"Number of 'E' answers for {character}: {E_count}")
    print(f"Number of invalid answers for {character}: {invalid}")

# Prepare the final JSON structure
final_output = {
    "data": data,
    "accuracy": accuracy_results,
}

# Save the modified data and accuracy to JSON
answers_save_path = os.path.join(save_dir, f"{task}_{size}_answers.json")
print("Saving generated answers and accuracy to JSON...")
with open(answers_save_path, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=4)
print(f"Saved answers and accuracy to {answers_save_path}")

print("All answers and accuracy have been saved successfully.")