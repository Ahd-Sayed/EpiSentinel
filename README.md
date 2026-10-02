[README.md](https://github.com/user-attachments/files/32940220/README.md)
# EpiSentinel

**AI-powered epidemic early warning system for African health ministries**

Digital Innovation Challenge 2026 · Track: Digital Health

EpiSentinel analyzes hospital visit data with three complementary AI models and fuses their outputs into a three-level alert system (**Watch / Warning / Emergency**), helping health decision-makers detect outbreaks days or weeks earlier than traditional manual surveillance.

---

## Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [How It Works](#how-it-works)
- [Key Features](#key-features)
- [Models](#models)
- [Dashboard](#dashboard)
- [Data](#data)
- [Project Structure](#project-structure)
- [Dataset](#dataset)
- [Results & Validation](#results--validation)
- [Challenges & Lessons Learned](#challenges--lessons-learned)
- [Tech Stack](#tech-stack)
- [Team](#team)
- [نبذة بالعربي](#نبذة-بالعربي)

---

## Problem

Countries like Egypt face recurring infectious disease challenges, such as the vaccine-derived poliovirus outbreak (VDPV2) in 2020–2021 and avian influenza cases (H5N1/H5N8) in 2022–2024. Digital health infrastructure is growing, but traditional surveillance still relies heavily on manual reports and after-the-fact analysis, which can delay outbreak detection by days or weeks.

The gap is not a lack of data. It is the lack of an intelligent system that continuously analyzes that data and flags early outbreak signals across cities and diseases.

Existing tools fall short for this use case:

| Tool | Limitation |
|---|---|
| SORMAS, DHIS2 / Africa CDC EMS | Manage the response after an outbreak is recorded; not ML-based early prediction |
| AfyaNet | Early-warning concept, but built on crowdsourcing rather than actual hospital visit data |
| WHO EIOS | Monitors open sources such as news, not clinical data |
| BlueDot, Metabiota | Use AI for prediction, but are priced for global clients and out of reach for budget-limited African ministries |

## Solution

EpiSentinel is a web platform for health authorities. It is not a mobile app or an isolated research model. It combines:

- an **AI analysis engine** (three models + a fusion engine),
- a **REST API**, and
- an **interactive dashboard**.

It brings together three capabilities that rarely exist in a single tool: visit-level anomaly detection, weekly trend forecasting, and a fusion mechanism that suppresses random false alarms.

## How It Works

```
CSV upload
   │
   ▼
Dataset validation → Data cleaning → Feature preparation
   │
   ├──► Isolation Forest ─┐   (visit-level anomalies)
   ├──► DBSCAN ───────────┤   (visit-level clusters / anomalies)
   └──► LSTM ─────────────┘   (weekly outbreak probability per city & disease)
                          │
                          ▼
                Fusion Scoring Engine
                          │
                          ▼
     Alert level per (city, disease, week):
            Watch / Warning / Emergency
                          │
                          ▼
   Database → Dashboard · PDF/CSV reports · REST API
```

1. **Cleaning and normalization** of uploaded visit data.
2. **Visit-level analysis** with Isolation Forest and DBSCAN to flag abnormal patterns.
3. **Weekly trend analysis** with an LSTM that predicts the probability of an outbreak in the coming week.
4. **Fusion engine** that combines all three outputs into a single alert decision.

**Inputs:** hospital visit records (visit date, city, disease, symptoms, basic demographics such as age).
**Outputs:** an alert level (Watch / Warning / Emergency) per city and disease each week, plus exportable reports.

## Key Features

| # | Component | Description |
|---|---|---|
| 1 | Anomaly detection engine | Isolation Forest + DBSCAN on individual visit records |
| 2 | LSTM outbreak forecasting | Ensemble of 3 BiLSTM models predicting next-week outbreak probability from the previous 8 weeks, per city and disease |
| 3 | Fusion engine | Weighted scoring that issues three-level alerts |
| 4 | Interactive dashboard | Live alerts, city heatmaps, and per-disease/city trends |
| 5 | Report export | Filtered alert records as PDF and CSV |
| 6 | Historical prediction database | Stores predictions and alerts to track performance against real outbreaks over time |

## Models

**Isolation Forest + DBSCAN.** Detect unusual patterns at the individual-visit level. To make DBSCAN practical on millions of records, the 28 symptom dimensions are reduced to 8 components with PCA, and clustering runs separately per (city, disease) instead of on the whole dataset at once.

**LSTM (BiLSTM ensemble).** Works at the weekly level. Weekly counts are aggregated for each (city, disease) pair, and the model predicts outbreak probability for the following week.

**Fusion Engine.** Uses a weighted point system (Isolation Forest +1, DBSCAN +2, LSTM +2) so that no single model can push an alert to the highest level on its own. Each model compensates for the others' weaknesses, which reduces false alarms.

## Dashboard

The web dashboard (Flask backend + HTML/JavaScript frontend) includes:

- **Upload & Pipeline Runs:** upload a CSV and run the full pipeline.
- **Analytics:** results for the uploaded dataset via *Overview*, *Alerts Explorer*, and *Data Explorer*, with maps and charts.
- **Model Performance** and **Scenario:** fixed pages that show model metrics and available scenarios, independent of the uploaded dataset.
- **Filtering** by city, disease, and alert level.
- **Export** to PDF and CSV, or programmatic access through the **REST API**.

<!-- Add screenshots here, e.g. ![Overview](docs/images/overview.png) -->

## Data

Real, labeled hospital visit data at the required scale was not available, and most public epidemic datasets reflect US/Western contexts. The team therefore generated a **calibrated synthetic dataset**:

- 64 African cities across 19 countries (27 of them Egyptian cities, about 42% of the data)
- More than 6 million visit records
- 12 real historical outbreak scenarios embedded as validation checkpoints (two of them Egyptian)

This dataset is intended as a foundation for developing and validating the models before retraining on real Egyptian data in the next phase.

## Project Structure

```
EpiSentinel/
├── app.py                  # Flask application entry point
├── wsgi.py                 # WSGI entry point for deployment
├── full_pipeline.py        # end-to-end analysis pipeline
├── app/                    # application code
├── task1_3_dir/            # anomaly detection stage (Isolation Forest, DBSCAN)
├── task2_dir/              # LSTM data and training stage
├── task2_models_dir/       # trained LSTM models
├── tests/                  # tests
├── data/                   # links to the datasets hosted on Kaggle
├── setup_db.py, db_import.py, check_*.py   # database setup and checks
├── *.csv, task4_summary.json                # sample inputs and validation outputs
├── requirements.txt
├── Procfile, nixpacks.toml                  # deployment configuration
└── .env.example            # environment variables template
```

## Dataset

The full datasets are too large for GitHub (the master dataset is about 525 MB, and GitHub limits files to 100 MB), so they are hosted on Kaggle:

| Dataset | Description |
|---|---|
| [EpiSentinel Synthea to African Data](https://www.kaggle.com/datasets/ahdsayedattia/episentinel-synthea-to-african-data) | Processed dataset: `master_dataset.zip` (~525 MB) and `weekly_cases_enhanced.zip` (~24 MB) |
| [Synthea Raw Output](https://www.kaggle.com/datasets/ahdsayedattia/synthea-raw-output) | Raw Synthea files for 100,000 patients: patients, encounters, conditions, organizations |

See the `data/` folder for a short description of each dataset. Small sample files used for testing are included in this repository.

## Results & Validation

- **Temporal hold-out testing:** 70/15/15 split so the models never see future data during training.
- **Historical scenario validation:** all **12 of 12** historical outbreak scenarios were detected, with an average early-warning lead time of **about 5 weeks**.
- **Live test on new real-world data:** cholera data from WHO reports for the Democratic Republic of the Congo and Mozambique (January–March 2026), fully outside the training data. The system flagged the documented rise in cases and issued **Emergency** alerts in the same week the official reports showed the increase.
- **Full pipeline runtime:** completed in about 3.3 seconds in the live run.

> No formal user-testing sessions with health workers or decision-makers have been conducted yet. They are planned for the next phase, once a pilot partnership is secured.

## Challenges & Lessons Learned

| Challenge | Approach |
|---|---|
| Public epidemic datasets are mostly US/Western | Built a calibrated synthetic African dataset with real historical outbreak checkpoints, then validated on real WHO data |
| DBSCAN on 6M+ records is memory-heavy | PCA (28 → 8 dimensions) and per-(city, disease) clustering |
| Combining models with different time granularities | Weighted fusion scoring so no single model can trigger the top alert alone |
| Unseen city/country names at inference time broke the LSTM encoders | Validation layer that excludes unknown categories from the LSTM only, keeps the other models running, and logs a clear warning |
| Five members building different pipeline stages independently | Explicit data contracts between stages: required columns, defaults for missing values, and output formats |

## Tech Stack

- **Backend:** Python, Flask
- **ML:** Isolation Forest, DBSCAN, PCA, LSTM/BiLSTM
- **Frontend:** HTML, JavaScript
- **Outputs:** REST API, PDF/CSV export, database for prediction history


## Team

| Name | Field |
|---|---|
| Mustafa Tamer (Team Lead) | Intelligent Systems, Faculty of AI, Menoufia University |
| Yahia Sanad | Intelligent Systems, Faculty of AI, Menoufia University |
| Ahd Sayed | Data Science, Faculty of AI, Menoufia University |
| Hanaa Hemdan | Data Science, Faculty of AI, Menoufia University |
| Mohamed Atia | Mechatronics, Faculty of Engineering, Zagazig National University |

---

## نبذة بالعربي

**EpiSentinel (فريق مستكشف الأوبئة)** نظام إنذار مبكر للأوبئة مدعوم بالذكاء الاصطناعي، موجّه لوزارات الصحة (بدءًا من مصر). يحلل بيانات زيارات المستشفيات بثلاثة نماذج متكاملة (Isolation Forest وDBSCAN وLSTM)، ثم يدمج نتائجها في محرك قرار يصدر تنبيهات على ثلاثة مستويات: **Watch / Warning / Emergency** لكل مدينة ومرض كل أسبوع.

يتضمن النظام لوحة تحكم تفاعلية، وواجهة برمجية (REST API)، وتصدير تقارير بصيغتي PDF وCSV.

تم التحقق من النظام على 12 سيناريو تفشٍّ تاريخي (اكتشاف 12 من 12 بمتوسط إنذار مبكر حوالي 5 أسابيع)، وعلى بيانات كوليرا حقيقية من تقارير منظمة الصحة العالمية خارج بيانات التدريب.
