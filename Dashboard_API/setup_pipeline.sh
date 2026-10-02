#!/bin/bash
# EpiGuard Africa - Pipeline Setup Script

# Make sure you place the training data CSV at the path specified below, or modify the path accordingly.
TRAIN_DATA_PATH="path/to/train_data.csv"

echo "Generating Day Index Reference JSON for EpiSentinel Pipeline..."

if [ ! -f "$TRAIN_DATA_PATH" ]; then
    echo "Error: Train data CSV not found at $TRAIN_DATA_PATH"
    echo "Please edit setup_pipeline.sh to point to the correct training dataset."
    exit 1
fi

python prepare_day_index_reference.py --train-data "$TRAIN_DATA_PATH" --out "task1_3_dir/day_index_ref.json"

echo "Setup complete."
