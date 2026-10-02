# Task 1 & 3 Artifacts Directory

This directory must contain the following required machine learning artifacts:
- `task3_iso_forest.pkl`
- `task3_dbscan.pkl`
- `day_index_ref.json`

**Note on `day_index_ref.json`**:
If this file is missing, you must generate it using the setup script:
```bash
python prepare_day_index_reference.py --train-data "path/to/train_data.csv" --out "task1_3_dir/day_index_ref.json"
```

The pipeline will crash if these files are not present.
