#!/bin/bash
# Created on Tue Dec 24 10:18:42 2024
# Author: paveenhuang

# Define the list of tasks
TASKS=(
"human_aging"
"jurisprudence"
"management"
"marketing"
"medical_genetics"
"miscellaneous"
"moral_disputes"
"moral_scenarios"
"nutrition"
"philosophy"
"prehistory"
"professional_accounting"
)

# Define the list of model sizes
# SIZES=("0.5B" "3B" "7B")
# MODELS=("qwen2.5")

# SIZES=("1B" "3B" "8B")
SIZES=("8B")
MODELS=("llama3")

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the directory where the script is located
cd "$SCRIPT_DIR"

# Number of tasks to execute in parallel (adjust according to your CPU core count)
JOBS=1

# Prepare all combinations of tasks, models, and sizes
COMBINATIONS=()
for TASK in "${TASKS[@]}"; do
    for MODEL in "${MODELS[@]}"; do
        for SIZE in "${SIZES[@]}"; do
            COMBINATIONS+=("$TASK $MODEL $SIZE")
        done
    done
done

# Debugging: print combinations
echo "Task-Model-Size Combinations to Process:"
for COMBINATION in "${COMBINATIONS[@]}"; do
    echo "$COMBINATION"
done

# Execute using GNU parallel
# Ensure GNU parallel is installed: sudo apt-get install parallel
echo "Starting parallel execution with $JOBS jobs..."
parallel -j "$JOBS" python3 /data2/paveen/RolePlaying/src/models/components/get_answer.py ::: "${COMBINATIONS[@]}"

# Check if parallel execution was successful
if [ $? -eq 0 ]; then
    echo "All tasks have been processed successfully."
else
    echo "An error occurred during parallel execution."
    exit 1
fi