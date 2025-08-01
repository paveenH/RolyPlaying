#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch answer-generation & accuracy script
Replaces per-task shell calls by looping over TASKS list in one run.
Author: paveenhuang
"""
import os
import json
import re
import torch
from tqdm import tqdm  # optional progress bar
from llms import VicundaModel
from detection.task_list import TASKS


# ── Configuration ────────────────────────────────────────────────────────────

LABEL_MAPPING = ["A", "B", "C", "D"]

def make_characters(task_name: str, type_: str):
    if type_ == "none":
        task_name = task_name.replace("_", " ")
        return [
            f"none {task_name}",
            f"{task_name}",
        ]
    elif type_ == "non-":
        task_name = task_name.replace("_", "-")
        return [
            f"non-{task_name}",
            f"{task_name}",
        ]
    elif type_ == "non":
        task_name = task_name.replace("_", " ")
        return [
            f"non {task_name}",
            f"{task_name}",
        ]
    else:
        return

# ── Helper functions (unchanged, trimmed for brevity) ────────────────────────
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cleaning(text: str):
    # text = text.replace("<|assistant|>", "")
    text = text.replace("<|assistant|>", "").replace("\u200b", "").strip().upper()
    # m = re.search(r"\b([A-E])\b", text.upper())
    m = re.search(r"(?<![A-Z])([A-E])(?![A-Z])", text)
    return m.group(1) if m else text.strip().upper()


def generate_answer(vc, prompt, diffusion_mode):
    if diffusion_mode == "dream":
        out = vc.generate_diffusion_dream(
            [prompt],
            max_new_tokens=SHORT,
            steps=STEP,
            top_p=1,
            temperature=0,
        )[0]
    elif diffusion_mode == "llada":
        out = vc.generate_diffusion_llada(
            [prompt],
            max_new_tokens=SHORT,
            steps=STEP,
            block_len=SHORT,
        )[0]
    else:
        out = vc.generate([prompt], max_new_tokens=SHORT)[0]

    return cleaning(out)


def extract_full_correct_text(question_text: str, label_idx: int):
    prefix = f"{LABEL_MAPPING[label_idx]})"
    for line in question_text.split("\n"):
        s = line.strip()
        if s.upper().startswith(prefix):
            return s[len(prefix) :].strip().lower()
    return None


def handle_invalid_answer(vc, prompt, true_text, true_label, diffusion_mode=False):
    if diffusion_mode == "dream":
        out_long = vc.generate_diffusion_dream(
            [prompt],
            max_new_tokens=LONG,
            steps=STEP,
            top_p=1,
            temperature=0,
        )[0].strip()
    elif diffusion_mode == "llada":
        out_long = vc.generate_diffusion_llada(
            [prompt],
            max_new_tokens=LONG,
            steps=STEP,
            block_len=LONG,
        )[0].strip()
    else:
        out_long = vc.generate([prompt], max_new_tokens=LONG)[0].strip()

    out_long = out_long.replace("<|assistant|>", "").replace("\u200b", "").strip().upper()
    extracted = cleaning(out_long)

    if extracted in LABEL_MAPPING:
        if extracted == true_label:
            return "[Add]" + extracted + out_long, True, False
        else:
            return extracted + out_long, False, False

    if extracted == "E":
        return "[Add]" + out_long, False, True

    if true_text and true_text.lower() in out_long.lower():
        return "[Add]" + out_long + "contains" + true_text, True, False

    if "i am not sure" in out_long.lower():
        return "[Add]" + out_long, False, True

    return out_long, False, False


# -------------------------------------------------------------------
def update(acc, char, status):
    acc[char][status] += 1


def run_task(vc, template, task):
    data = load_json(os.path.join(PATH_MMLU, f"{task}.json"))
    chars = make_characters(task, TYPE)
    print("characters:", chars)
    acc = {c: {"correct": 0, "E": 0, "invalid": 0, "total": 0} for c in chars}
    
    with torch.no_grad():    
        for idx, sample in enumerate(tqdm(data, desc=task)):
            ctx = sample["text"]
            true_idx = sample["label"]
            true_label = LABEL_MAPPING[true_idx]
            true_text = extract_full_correct_text(ctx, true_idx)

            for ch in chars:
                prompt = template.format(character=ch, context=ctx)
                ans = generate_answer(vc, prompt, DIFFUSION)
                # tqdm.write(f"▶ BEFORE   repr(orig): {repr(ans)}")
                # salvage if necessary
                if ans not in LABEL_MAPPING and ans != "E":
                    ans, is_corr, is_E = handle_invalid_answer(vc, prompt, true_text, true_label, DIFFUSION)
                    # tqdm.write(f"▶ AFTER    repr(rescued): {repr(ans)}")
                    if is_corr:
                        status = "correct"
                        tqdm.write(f"[{idx}][{ch}] '{ans}' -> Correct")
                    elif is_E:
                        status = "E"
                        tqdm.write(f"[{idx}][{ch}] '{ans}' -> E")
                    else:
                        status = "invalid"
                        tqdm.write(f"[{idx}][{ch}] '{ans}' -> Invalid")
                else:
                    status = "correct" if ans == true_label else ("E" if ans == "E" else "invalid")

                acc[ch]["total"] += 1
                update(acc, ch, status)

                sample[f"answer_{ch.replace(' ','_')}"] = ans

    # summarise
    summary = {}
    for ch, c in acc.items():
        pct = (c["correct"] / c["total"]) * 100 if c["total"] else 0
        summary[ch] = {
            "correct": c["correct"],
            "E_count": c["E"],
            "invalid": c["invalid"],
            "total": c["total"],
            "accuracy_percentage": round(pct, 2),
        }
    return data, summary


def main():
    print(f"Loading model {MODEL}/{SIZE}…")
    vc = VicundaModel(model_path=MODEL_DIR, diffusion_mode=DIFFUSION)
    template = vc.template
    vc.model.eval()
    save_dir = os.path.join(SAVE_BASE, MODEL)
    os.makedirs(save_dir, exist_ok=True)

    for task in TASKS:
        print(f"\n=== {task} ===")
        print(template)
        data, acc = run_task(vc, template, task)

        out = os.path.join(save_dir, f"{task}_{SIZE}_answers.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"data": data, "accuracy": acc}, f, ensure_ascii=False, indent=2)
        print(f"[Saved] {out}")

        for ch, r in acc.items():
            print(
                f"{ch:>18}: {r['accuracy_percentage']}% "
                f"(correct {r['correct']}/{r['total']}, "
                f"E {r['E_count']}, invalid {r['invalid']})"
            )

    print("\n✅  All tasks finished.")

if __name__ == "__main__":
    MODEL = "pih4"
    SIZE = "4B"
    TYPE = "non"

    # fixed paths
    PATH_MMLU = "/data2/paveen/RolePlaying/components/mmlu"
    SAVE_BASE = f"/data2/paveen/RolePlaying/components/answer_{TYPE}"

    # MODEL_DIR = f"/data2/paveen/RolePlaying/shared/{MODEL}/{SIZE}"
    # MODEL_DIR = "NousResearch/Hermes-3-Llama-3.2-3B"
    # MODEL_DIR = "meta-llama/Llama-3.2-3B-Instruct"  
    # MODEL_DIR = "meta-llama/Llama-3.1-8B-Instruct"
    # MODEL_DIR = "mistralai/Mistral-7B-Instruct-v0.3"
    # MODEL_DIR = "openchat/openchat_3.5"
    # MODEL_DIR = "HuggingFaceH4/zephyr-7b-beta"
    # MODEL_DIR =  "mistralai/Mistral-7B-v0.3"
    # MODEL_DIR = "Qwen/Qwen2.5-3B-Instruct"
    MODEL_DIR = "microsoft/Phi-4-mini-instruct"
    print (MODEL_DIR)

    SHORT = 2
    LONG = 12

    DIFFUSION = None  # dream/ llada/ None
    STEP = 16
    main()
