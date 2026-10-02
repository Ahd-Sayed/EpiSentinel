# Task 2 Models Directory

This directory must contain the Keras neural network models required by the EpiSentinel LSTM ensemble.

Expected files:
- `model_Ebola_virus_disease.keras` (or similar depending on trained diseases)
- `model_Cholera.keras`
- `model_COVID-19.keras`
- `model_Malaria.keras`
- `model_Mpox.keras`
- `model_Dengue_fever.keras`
- `model_Lassa_fever.keras`
- `model_Meningitis.keras`
- `model_Typhoid_fever.keras`

The pipeline will dynamically load models from this directory matching the diseases found in the uploaded datasets.
