#!/bin/bash

models=("gpt-4.1-mini" "gpt-4.1" "gpt-5-mini" "gpt-5")
# models=("gemini-2.5-flash")
retries=(1 3)

# mkdir -p _log

for model in "${models[@]}"; do
  for r in "${retries[@]}"; do
    log_name="_log/running_log_${model//./}_${r}"
    echo "Running model=$model max_retries=$r"
    model="$model" max_retries="$r" python run.py > "$log_name"
  done
done
