#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch hidden-state extraction for multiple tasks, sizes, and models.
Author: paveenhuang
"""

import os
import json
import numpy as np
from tqdm import tqdm
from vicuna import VicundaModel

# ── Configuration ────────────────────────────────────────────────────────────
TASKS = [
    "abstract_algebra",
    "anatomy",
    "astronomy",
    "business_ethics",
    "clinical_knowledge",
    "college_biology",
    "college_chemistry",
    "college_computer_science",
    "college_medicine",
    "college_mathematics",
    "college_physics",
    "computer_security",
    "conceptual_physics",
    "econometrics",
    "electrical_engineering",
    "elementary_mathematics",
    "formal_logic",
    "global_facts",
    "high_school_biology",
    "high_school_chemistry",
    "high_school_computer_science",
    "high_school_european_history",
    "high_school_geography",
    "high_school_government_and_politics",
    "high_school_macroeconomics",
    "high_school_mathematics",
    "high_school_microeconomics",
    "high_school_physics",
    "high_school_psychology",
    "high_school_statistics",
    "high_school_us_history",
    "high_school_world_history",
    "human_aging",
    "human_sexuality",
    "international_law",
    "jurisprudence",
    "logical_fallacies",
    "machine_learning",
    "management",
    "marketing",
    "medical_genetics",
    "miscellaneous",
    "moral_disputes",
    "moral_scenarios",
    "nutrition",
    "philosophy",
    "prehistory",
    "professional_accounting",
    "professional_law",
    "professional_medicine",
    "professional_psychology",
    "public_relations",
    "security_studies",
    "sociology",
    "us_foreign_policy",
    "virology",
    "world_religions"
]
MODEL_LIST = ["openchat"]  # example models
SIZE_LIST = ["7B"]               # example sizes
# MODEL_DIR = os.path.join("/data2/paveen/RolePlaying/shared", model, size)
MODEL_DIR = "openchat/openchat_3.5"


# Output base directory for hidden states
BASE_SAVE_DIR = "/data2/paveen/RolePlaying/src/models/components/hidden_states_v3"
# Path to MMLU JSON files
PATH_MMLU = "/data2/paveen/RolePlaying/src/models/components/mmlu"

# Characters for hidden-state extraction
def make_characters(task_name: str):
    task_name = task_name.replace("_", " ")
    return [f"non-{task_name}",
            f"{task_name}",
            ]

# Iterate over models, sizes, and tasks
for model in MODEL_LIST:
    for size in SIZE_LIST:
        # Initialize model
        print(f"Loading model {model}/{size}...")
        vc = VicundaModel(model_path=MODEL_DIR)
        template = vc.template
        print(f"Template: {template}\n")

        # Prepare save directory for this model
        model_save_dir = os.path.join(BASE_SAVE_DIR, model)
        os.makedirs(model_save_dir, exist_ok=True)

        # Process each task
        for task in TASKS:
            # Load JSON
            json_path = os.path.join(PATH_MMLU, f"{task}.json")
            print(f"Loading JSON data from {json_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Total samples for {task}: {len(data)}")

            # Storage for hidden states
            characters = make_characters(task)
            hidden_states_storage = {ch: [] for ch in characters}

            # Extract hidden states per sample
            print(f"Processing task {task}...")
            for idx, sample in enumerate(tqdm(data, desc=f"{model}/{size}/{task}")):
                context = sample.get("text", "")
                if not context:
                    tqdm.write(f"Sample {idx} missing text; skipping.")
                    continue

                for character in characters:
                    prompt = template.format(character=character, context=context)
                    hidden_states = vc.get_hidden_states(
                        prompt=prompt,
                        character=character
                    )
                    # Validate
                    if any(pos is None for pos in hidden_states):
                        tqdm.write(f"Sample {idx}, '{character}' missing hidden states; skipping.")
                        continue
                    # Stack and store
                    hs_array = np.stack([np.stack(pos, axis=0) for pos in hidden_states], axis=0)
                    hidden_states_storage[character].append(hs_array)

            # Save hidden states
            print(f"Saving hidden states for {task}...")
            for character, hs_list in hidden_states_storage.items():
                if not hs_list:
                    tqdm.write(f"No hidden states for '{character}' in task {task}; skipping save.")
                    continue
                hs_array = np.stack(hs_list, axis=0)
                char_safe = character.replace(" ", "_")
                save_path = os.path.join(model_save_dir, f"{char_safe}_{task}_{size}.npy")
                np.save(save_path, hs_array)
                print(f"Saved: {save_path}")

        print(f"Completed model {model}/{size}\n")

print("All models and tasks processed.")