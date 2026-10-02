"""
EpiSentinel — full_pipeline(): the ONE function that turns a raw patient-visit CSV
into final fused outbreak alerts (Normal / Watch / Warning / Emergency).

SELF-CONTAINED: every transformation in this file is copied directly from logic that
already exists in your own project notebooks:
    - weekly_cases_pipeline.ipynb        -> _aggregate_weekly()
    - EpiSentinel_Tasks1_3_v6.ipynb      -> AGE/LAT/LON/COMORBIDITY scaling
    - EpiSentinel_Task2_LSTM_Model4.ipynb -> _lstm_build_features() / _lstm_build_windows()
    - Task4.ipynb                         -> DAY_INDEX_NORM, RECENT_CASE_COUNT_NORM,
                                              Isolation Forest, DBSCAN, fusion rule
Nothing here is invented data or an external dependency — it only reads artifact files
that your notebooks already save, plus ONE small derived file explained at the bottom
of this docstring (day_index_ref.json).

REQUIRED ARTIFACTS (all produced by your existing notebooks — nothing extra to generate,
except day_index_ref.json, see below):

  task1_3_dir/  (= wherever EpiSentinel_Tasks1_3_v6.ipynb's "artifacts/" folder ends up)
      scaler.pkl                 <- Step 5 of Tasks1_3 (AGE_AT_VISIT, LAT, LON, COMORBIDITY_COUNT)
      case_rate_scaler.pkl       <- saved by the notebook alongside the others
      task3_iso_forest.pkl
      task3_pca.pkl
      task3_dbscan_params.pkl
      task3_metadata.json        <- (in the notebook's "results/" folder — for the DBSCAN threshold)
      day_index_ref.json         <- NOT saved by the notebook today, see explanation below

  task2_dir/    (= EpiSentinel_Task2_LSTM_Model4.ipynb's "artifacts/" folder)
      encoders.joblib
      scalers.joblib
      best_threshold.json

  task2_models_dir/  (= Task2 notebook's "checkpoints/" folder)
      best_model_seed42.keras, best_model_seed123.keras, best_model_seed2024.keras

------------------------------------------------------------------------------------
WHAT IS day_index_ref.json, AND WHY DOES IT EXIST IF IT'S NOT ONE OF YOUR SAVED FILES?
------------------------------------------------------------------------------------
Inside Task4.ipynb, DAY_INDEX_NORM is computed like this:

    t0 = train_df["VISIT_DATE"].min()                          # earliest date in train_data.csv
    day_max = (train_df["VISIT_DATE"] - t0).dt.days.max()       # date range of train_data.csv, in days
    DAY_INDEX_NORM = (VISIT_DATE - t0).days / day_max

`t0` and `day_max` are just two numbers, computed FROM train_data.csv (an artifact you
already have). Task4.ipynb recomputes them every time by reloading the whole
train_data.csv file. That's fine inside a notebook, but a live API shouldn't have to
load a multi-million-row training file on every prediction just to get two numbers.

So `day_index_ref.json` is nothing new — it is exactly those same two numbers, computed
once from your own train_data.csv, saved to a tiny file so the API can read them
instantly instead of reloading train_data.csv on every request. It contains ONLY this:

    {"t0": "2000-01-03", "day_max": 9500.0}

`prepare_day_index_reference.py` (included) generates it for you — run it once:

    python prepare_day_index_reference.py --train-data "path/to/train_data.csv" \
        --out "path/to/task1_3_dir/day_index_ref.json"

That's it — no new data, just a one-time extraction of two numbers your project already
implicitly depends on.
"""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.cluster import DBSCAN

# ============================================================================
# Constants — copied verbatim from the notebooks. Do not change without
# re-validating against the notebooks' own printed metrics.
# ============================================================================

SYM_COLS = [
    "sym_fever", "sym_chills", "sym_headache", "sym_fatigue", "sym_vomiting", "sym_diarrhea",
    "sym_cough", "sym_shortness_of_breath", "sym_chest_pain", "sym_rash", "sym_muscle_pain",
    "sym_abdominal_pain", "sym_night_sweats", "sym_weight_loss", "sym_jaundice", "sym_stiff_neck",
    "sym_sensitivity_to_light", "sym_red_eyes", "sym_runny_nose", "sym_sore_throat",
    "sym_hemorrhage", "sym_sweating", "sym_dehydration", "sym_muscle_cramps", "sym_loss_of_smell",
    "sym_swollen_lymph_nodes", "sym_pain_behind_eyes", "sym_general_weakness",
]  # EpiSentinel_Tasks1_3_v6.ipynb, Step 1 printed column list

REQUIRED_VISIT_COLUMNS = ["VISIT_DATE", "CITY", "COUNTRY", "DISEASE"]
CASE_RATE_WINDOW_DAYS = 7  # Task4.ipynb

LSTM_GROUP_COLS = ["COUNTRY", "CITY", "DISEASE"]
LSTM_DATE_COL = "VISIT_WEEK_START"
LSTM_SEQ_LEN = 8  # EpiSentinel_Task2_LSTM_Model4.ipynb

LSTM_SEQ_NUMERIC_COLS = [
    "VISIT_YEAR_s", "month_sin", "month_cos",
    "case_count_s", "avg_age_s", "avg_comorbidity_s",
    "lag_1_cases_s", "lag_2_cases_s", "lag_3_cases_s", "lag_4_cases_s",
    "cases_2wk_avg_s", "cases_3wk_avg_s", "cases_4wk_avg_s", "cases_4wk_std_s",
    "cases_diff_s", "pct_change_wow_s", "growth_rate_s", "case_zscore_s",
]  # EpiSentinel_Task2_LSTM_Model4.ipynb, SEQ_NUMERIC_COLS

# Task4.ipynb / EpiSentinel_Task4_TeamSummary.pdf fusion rule
POINTS = {"if": 1, "dbscan": 2, "lstm": 2}
ALERT_LEVELS = [(0, "Normal"), (1, "Watch"), (3, "Warning"), (4, "Emergency")]


def points_to_alert(points: int) -> str:
    level = "Normal"
    for threshold, name in ALERT_LEVELS:
        if points >= threshold:
            level = name
    return level


def focal_loss(gamma=2.0, alpha=0.75):
    """Only needed to load the .keras files if they were saved with compile=True.
    Task4.ipynb itself loads with compile=False (no loss needed) — kept here only as
    a safe fallback in case a model file requires it."""
    def loss_fn(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        eps = tf.keras.backend.epsilon()
        y_pred = tf.clip_by_value(y_pred, eps, 1 - eps)
        pt = tf.where(tf.equal(y_true, 1), y_pred, 1 - y_pred)
        alpha_t = tf.where(tf.equal(y_true, 1), alpha, 1 - alpha)
        return -tf.reduce_mean(alpha_t * tf.pow(1 - pt, gamma) * tf.math.log(pt))
    return loss_fn


@dataclass
class PipelineWarnings:
    missing_symptom_cols_filled: list = field(default_factory=list)
    rows_with_fallback_age: int = 0
    rows_with_fallback_latlon: int = 0
    unseen_disease_for_lstm: list = field(default_factory=list)
    unseen_city_country_for_lstm: list = field(default_factory=list)
    groups_too_short_for_lstm: list = field(default_factory=list)
    rows_dropped_bad_dates: int = 0


class EpiSentinelFullPipeline:
    def __init__(self, task1_3_dir="artifacts_task1_3", task2_dir="artifacts_task2",
                 task2_models_dir="models_task2"):
        # ---- Task1/3 artifacts ----
        self.if_model = self._load_pickle(os.path.join(task1_3_dir, "task3_iso_forest.pkl"))
        self.pca = self._load_pickle(os.path.join(task1_3_dir, "task3_pca.pkl"))
        self.dbscan_params = self._load_pickle(os.path.join(task1_3_dir, "task3_dbscan_params.pkl"))
        self.task1_scaler = self._load_pickle(os.path.join(task1_3_dir, "scaler.pkl"))
        self.case_rate_scaler = joblib.load(os.path.join(task1_3_dir, "case_rate_scaler.pkl"))

        with open(os.path.join(task1_3_dir, "task3_metadata.json")) as f:
            task3_meta = json.load(f)
        self.dbscan_threshold = task3_meta["models"]["DBSCAN"]["threshold"]

        day_index_ref_path = os.path.join(task1_3_dir, "day_index_ref.json")
        if not os.path.exists(day_index_ref_path):
            raise FileNotFoundError(
                f"Missing {day_index_ref_path}. This is not a bug — it's a one-time setup "
                f"step. Run: python prepare_day_index_reference.py --train-data "
                f"<path to your train_data.csv> --out {day_index_ref_path}"
            )
        with open(day_index_ref_path) as f:
            ref = json.load(f)
        self.t0 = pd.Timestamp(ref["t0"])
        self.day_max = float(ref["day_max"])

        # ---- Task2 artifacts ----
        with open(os.path.join(task2_dir, "best_threshold.json")) as f:
            self.lstm_threshold = float(json.load(f)["best_threshold"])
        self.lstm_encoders = joblib.load(os.path.join(task2_dir, "encoders.joblib"))
        self.lstm_scalers = joblib.load(os.path.join(task2_dir, "scalers.joblib"))

        model_paths = sorted(
            p for p in os.listdir(task2_models_dir) if p.endswith(".keras")
        )
        if not model_paths:
            raise FileNotFoundError(f"No .keras files found in {task2_models_dir}")
        self.lstm_models = []
        for p in model_paths:
            full_path = os.path.join(task2_models_dir, p)
            try:
                self.lstm_models.append(tf.keras.models.load_model(full_path, compile=False))
            except Exception:
                self.lstm_models.append(
                    tf.keras.models.load_model(full_path, custom_objects={"loss_fn": focal_loss()})
                )

    @staticmethod
    def _load_pickle(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing artifact: {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    # ------------------------------------------------------------------
    # Step 1: validate + fill gaps in the raw upload
    # ------------------------------------------------------------------
    def _prepare_visits(self, raw_df: pd.DataFrame, warn: PipelineWarnings) -> pd.DataFrame:
        df = raw_df.copy()
        missing_required = set(REQUIRED_VISIT_COLUMNS) - set(df.columns)
        if missing_required:
            raise ValueError(f"Missing required columns: {sorted(missing_required)}")
        if len(df) == 0:
            raise ValueError("Uploaded file has no rows.")

        for col in SYM_COLS:
            if col not in df.columns:
                warn.missing_symptom_cols_filled.append(col)
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        df["VISIT_DATE"] = pd.to_datetime(df["VISIT_DATE"], errors="coerce")
        bad_dates = int(df["VISIT_DATE"].isna().sum())
        if bad_dates:
            warn.rows_dropped_bad_dates = bad_dates
            df = df.dropna(subset=["VISIT_DATE"])
        if len(df) == 0:
            raise ValueError("No rows left after dropping unparseable VISIT_DATE values.")

        if "VISIT_YEAR" not in df.columns:
            df["VISIT_YEAR"] = df["VISIT_DATE"].dt.year
        if "VISIT_MONTH" not in df.columns:
            df["VISIT_MONTH"] = df["VISIT_DATE"].dt.month

        if "SEASON" not in df.columns:
            df["SEASON"] = df["VISIT_MONTH"].apply(self._season_from_month)

        if "AGE_AT_VISIT" not in df.columns:
            df["AGE_AT_VISIT"] = np.nan
        df["AGE_AT_VISIT"] = pd.to_numeric(df["AGE_AT_VISIT"], errors="coerce")
        age_missing = df["AGE_AT_VISIT"].isna()
        if age_missing.any():
            warn.rows_with_fallback_age = int(age_missing.sum())
            # Simple, dependency-free fallback: median age of the rows that DO have an
            # age in this same upload; if literally none do, fall back to 30.0.
            fallback_age = df["AGE_AT_VISIT"].median()
            if pd.isna(fallback_age):
                fallback_age = 30.0
            df.loc[age_missing, "AGE_AT_VISIT"] = fallback_age

        if "COMORBIDITY_COUNT" not in df.columns:
            df["COMORBIDITY_COUNT"] = 0
        df["COMORBIDITY_COUNT"] = pd.to_numeric(df["COMORBIDITY_COUNT"], errors="coerce").fillna(0)

        for col in ["LAT", "LON"]:
            if col not in df.columns:
                df[col] = np.nan
            df[col] = pd.to_numeric(df[col], errors="coerce")
        latlon_missing = df["LAT"].isna() | df["LON"].isna()
        if latlon_missing.any():
            warn.rows_with_fallback_latlon = int(latlon_missing.sum())
            # Fallback: another row for the same CITY in this upload that does have
            # coordinates; otherwise 0.0 (visit still processed, geo signal just uninformative).
            city_latlon = (
                df.dropna(subset=["LAT", "LON"]).groupby("CITY")[["LAT", "LON"]].first()
            )
            for idx in df.index[latlon_missing]:
                city = df.at[idx, "CITY"]
                if city in city_latlon.index:
                    df.at[idx, "LAT"] = city_latlon.loc[city, "LAT"]
                    df.at[idx, "LON"] = city_latlon.loc[city, "LON"]
                else:
                    df.at[idx, "LAT"] = 0.0
                    df.at[idx, "LON"] = 0.0

        return df.reset_index(drop=True)

    @staticmethod
    def _season_from_month(month: int) -> str:
        # EXACT copy of weekly_cases_pipeline.ipynb's get_season()
        if month in [3, 4, 5]:
            return "Long_Rains"
        if month in [6, 7, 8]:
            return "Dry_Season"
        if month in [9, 10, 11]:
            return "Short_Rains"
        return "Cool_Dry"

    # ------------------------------------------------------------------
    # Step 2: visit-level engineered features — Task4.ipynb, verbatim
    # ------------------------------------------------------------------
    def _add_visit_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["DAY_INDEX"] = (df["VISIT_DATE"] - self.t0).dt.days.astype(float)
        df["DAY_INDEX_NORM"] = df["DAY_INDEX"] / self.day_max

        df = df.sort_values(["CITY", "DISEASE", "VISIT_DATE"]).reset_index(drop=True)
        counts = np.zeros(len(df))
        window = np.timedelta64(CASE_RATE_WINDOW_DAYS, "D")
        for (_city, _disease), grp in df.groupby(["CITY", "DISEASE"], sort=False):
            dates = grp["VISIT_DATE"].values
            idx = grp.index.values
            left = 0
            for right in range(len(dates)):
                while dates[right] - dates[left] > window:
                    left += 1
                counts[idx[right]] = right - left
        df["RECENT_CASE_COUNT"] = counts
        df["RECENT_CASE_COUNT_NORM"] = self.case_rate_scaler.transform(df[["RECENT_CASE_COUNT"]])

        norm_cols = self.task1_scaler.transform(df[["AGE_AT_VISIT", "LAT", "LON", "COMORBIDITY_COUNT"]])
        df["AGE_AT_VISIT_NORM"] = norm_cols[:, 0]
        df["COMORBIDITY_COUNT_NORM"] = norm_cols[:, 3]
        return df

    # ------------------------------------------------------------------
    # Step 3: Isolation Forest + DBSCAN (visit level) — Task4.ipynb, verbatim
    # ------------------------------------------------------------------
    def _run_if_dbscan(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.reset_index(drop=True)
        iso_features = SYM_COLS + ["DAY_INDEX_NORM", "AGE_AT_VISIT_NORM",
                                    "COMORBIDITY_COUNT_NORM", "RECENT_CASE_COUNT_NORM"]
        X_iso = df[iso_features].values
        raw_pred = self.if_model.predict(X_iso)
        df["if_pred"] = (raw_pred == -1).astype(int)
        df["if_score"] = self.if_model.decision_function(X_iso)

        pca_cols = [f"pca_{i}" for i in range(8)]
        df[pca_cols] = self.pca.transform(df[SYM_COLS].values)
        dbscan_features = pca_cols + ["DAY_INDEX_NORM", "RECENT_CASE_COUNT_NORM"]

        scores = np.zeros(len(df))
        eps, min_samples = self.dbscan_params["eps"], self.dbscan_params["min_samples"]
        for (_city, _disease), chunk in df.groupby(["CITY", "DISEASE"]):
            X = chunk[dbscan_features].values
            if len(X) < min_samples:
                continue  # too few visits in this group to form a cluster — scored 0 (not flagged), no crash
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
            for lbl in set(labels) - {-1}:
                mask = labels == lbl
                cluster_burst = chunk.loc[chunk.index[mask], "RECENT_CASE_COUNT"].mean()
                scores[chunk.index[mask]] = cluster_burst
        df["dbscan_score"] = scores
        df["dbscan_pred"] = (df["dbscan_score"] >= self.dbscan_threshold).astype(int)
        return df

    # ------------------------------------------------------------------
    # Step 4: raw visits -> weekly — weekly_cases_pipeline.ipynb, verbatim
    # ------------------------------------------------------------------
    @staticmethod
    def _aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["VISIT_WEEK_START"] = df["VISIT_DATE"].dt.to_period("W").apply(lambda r: r.start_time)

        weekly = df.groupby(["COUNTRY", "CITY", "DISEASE", "VISIT_WEEK_START"]).agg(
            case_count=("VISIT_DATE", "count"),
            avg_age=("AGE_AT_VISIT", "mean"),
            avg_comorbidity=("COMORBIDITY_COUNT", "mean"),
            VISIT_YEAR=("VISIT_YEAR", "first"),
            VISIT_MONTH=("VISIT_MONTH", "first"),
            SEASON=("SEASON", "first"),
            LAT=("LAT", "first"),
            LON=("LON", "first"),
        ).reset_index()
        weekly = weekly.sort_values(["CITY", "DISEASE", "VISIT_WEEK_START"]).reset_index(drop=True)

        for lag in [1, 2, 3, 4]:
            weekly[f"lag_{lag}_cases"] = (
                weekly.groupby(["CITY", "DISEASE"])["case_count"].shift(lag).fillna(0)
            )
        grouped = weekly.groupby(["CITY", "DISEASE"])["case_count"]
        weekly["cases_2wk_avg"] = grouped.transform(lambda x: x.rolling(2, min_periods=1).mean()).round(2)
        weekly["cases_3wk_avg"] = grouped.transform(lambda x: x.rolling(3, min_periods=1).mean()).round(2)
        weekly["cases_4wk_avg"] = grouped.transform(lambda x: x.rolling(4, min_periods=1).mean()).round(2)
        weekly["cases_4wk_std"] = grouped.transform(lambda x: x.rolling(4, min_periods=1).std().fillna(0)).round(2)
        weekly["cases_diff"] = weekly.groupby(["CITY", "DISEASE"])["case_count"].diff().fillna(0).round(2)
        weekly["pct_change_wow"] = (
            weekly.groupby(["CITY", "DISEASE"])["case_count"].pct_change()
            .fillna(0).replace([np.inf, -np.inf], 0).round(4)
        )
        weekly["growth_rate"] = (
            (weekly["case_count"] - weekly["cases_4wk_avg"]) / weekly["cases_4wk_avg"].clip(lower=1)
        ).round(4)
        return weekly

    # ------------------------------------------------------------------
    # Step 5: LSTM preprocessing + windowing — Task2 notebook, verbatim
    # ------------------------------------------------------------------
    def _lstm_transform_scale(self, df, col, out_col, scaler_key, log_transform=False, clip=None):
        work_col = col
        if clip is not None:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan).clip(*clip).fillna(0)
        if log_transform:
            work_col = col + "_log"
            df[work_col] = np.log1p(df[col])
            
        if scaler_key in self.lstm_scalers:
            df[out_col] = self.lstm_scalers[scaler_key].transform(df[[work_col]])
        else:
            df[out_col] = df[work_col]

    def _lstm_build_features(self, weekly_df: pd.DataFrame, warn: PipelineWarnings):
        df = weekly_df.copy()
        df[LSTM_DATE_COL] = pd.to_datetime(df[LSTM_DATE_COL])
        df = df.sort_values(LSTM_GROUP_COLS + [LSTM_DATE_COL]).reset_index(drop=True)

        # Unseen-category handling: rows whose CITY/COUNTRY/DISEASE/SEASON the LSTM's
        # encoders never saw are DROPPED here (LSTM skips them — they still got IF/DBSCAN
        # coverage upstream), never crash the whole batch.
        for col, enc_key in [("COUNTRY", "country"), ("CITY", "city"),
                              ("DISEASE", "disease"), ("SEASON", "season")]:
            encoder = self.lstm_encoders[enc_key]
            known = set(encoder.classes_)
            values = df[col].astype(str)
            unseen_mask = ~values.isin(known)
            if unseen_mask.any():
                unseen_vals = sorted(values[unseen_mask].unique().tolist())
                if col in ("CITY", "COUNTRY"):
                    warn.unseen_city_country_for_lstm.extend(f"{col}={v}" for v in unseen_vals)
                elif col == "DISEASE":
                    warn.unseen_disease_for_lstm.extend(unseen_vals)
            df = df[~unseen_mask].copy()
            if len(df) == 0:
                return df
            df[col + "_enc"] = encoder.transform(df[col].astype(str))

        df["month_sin"] = np.sin(2 * np.pi * df["VISIT_MONTH"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["VISIT_MONTH"] / 12)

        self._lstm_transform_scale(df, "VISIT_YEAR", "VISIT_YEAR_s", "VISIT_YEAR_s")
        self._lstm_transform_scale(df, "LAT", "LAT_s", "LAT_s")
        self._lstm_transform_scale(df, "LON", "LON_s", "LON_s")
        self._lstm_transform_scale(df, "case_count", "case_count_s", "case_count_log", log_transform=True)
        for lag_col in ["lag_1_cases", "lag_2_cases", "lag_3_cases", "lag_4_cases"]:
            df[lag_col + "_log"] = np.log1p(df[lag_col])
            df[lag_col + "_s"] = self.lstm_scalers["case_count_log"].transform(
                df[[lag_col + "_log"]].rename(columns={lag_col + "_log": "case_count_log"})
            )
        self._lstm_transform_scale(df, "avg_age", "avg_age_s", "avg_age_s")
        self._lstm_transform_scale(df, "avg_comorbidity", "avg_comorbidity_s", "avg_comorbidity_s")
        for col in ["cases_2wk_avg", "cases_3wk_avg", "cases_4wk_avg", "cases_4wk_std"]:
            self._lstm_transform_scale(df, col, col + "_s", col + "_s", log_transform=True)
        self._lstm_transform_scale(df, "cases_diff", "cases_diff_s", "cases_diff_s", clip=(-100, 100))
        self._lstm_transform_scale(df, "pct_change_wow", "pct_change_wow_s", "pct_change_wow_s", clip=(-5, 5))
        self._lstm_transform_scale(df, "growth_rate", "growth_rate_s", "growth_rate_s", clip=(-5, 5))

        lag_cols = ["lag_1_cases", "lag_2_cases", "lag_3_cases", "lag_4_cases"]
        lag_mean = df[lag_cols].mean(axis=1)
        lag_std = df[lag_cols].std(axis=1)
        df["case_zscore"] = (df["case_count"] - lag_mean) / (lag_std + 1)
        self._lstm_transform_scale(df, "case_zscore", "case_zscore_s", "case_zscore_s", clip=(-30, 30))
        return df

    def _lstm_predict_latest_window(self, feats: pd.DataFrame, warn: PipelineWarnings) -> pd.DataFrame:
        if len(feats) == 0:
            return pd.DataFrame(columns=["city", "disease", "as_of_week", "lstm_flag", "lstm_probability"])

        rows = {"seq_numeric": [], "season_seq": [], "country": [], "city": [], "disease": [],
                "latlon": [], "group": [], "as_of_date": []}
        for keys, g in feats.groupby(LSTM_GROUP_COLS):
            g = g.sort_values(LSTM_DATE_COL).reset_index(drop=True)
            n = len(g)
            if n < LSTM_SEQ_LEN:
                warn.groups_too_short_for_lstm.append(
                    f"{'/'.join(map(str, keys))} (has {n} weeks, needs >= {LSTM_SEQ_LEN})"
                )
                continue
            i = n - LSTM_SEQ_LEN
            rows["seq_numeric"].append(g[LSTM_SEQ_NUMERIC_COLS].values[i:i + LSTM_SEQ_LEN].astype(np.float32))
            rows["season_seq"].append(g["SEASON_enc"].values[i:i + LSTM_SEQ_LEN].astype(np.int32))
            rows["country"].append(g["COUNTRY_enc"].iloc[0])
            rows["city"].append(g["CITY_enc"].iloc[0])
            rows["disease"].append(g["DISEASE_enc"].iloc[0])
            rows["latlon"].append([g["LAT_s"].iloc[0], g["LON_s"].iloc[0]])
            rows["group"].append(keys)  # (country, city, disease) as given
            rows["as_of_date"].append(g[LSTM_DATE_COL].iloc[n - 1])

        if not rows["group"]:
            return pd.DataFrame(columns=["city", "disease", "as_of_week", "lstm_flag", "lstm_probability"])

        input_dict = {
            "seq_numeric": np.array(rows["seq_numeric"], dtype=np.float32),
            "season_seq": np.array(rows["season_seq"], dtype=np.int32),
            "country": np.array(rows["country"], dtype=np.int32),
            "city": np.array(rows["city"], dtype=np.int32),
            "disease": np.array(rows["disease"], dtype=np.int32),
            "latlon": np.array(rows["latlon"], dtype=np.float32),
        }

        # Handle OOV (Out of Vocabulary) unseen categorical values:
        # Clip encoded integers to the maximum valid index for the model's Embedding layers
        try:
            # Baseline max indices from training
            max_indices = {"season_seq": 3, "country": 18, "city": 63, "disease": 8}
            # Dynamically override by sniffing the actual Embedding layers in the loaded model
            for layer in self.lstm_models[0].layers:
                if isinstance(layer, tf.keras.layers.Embedding):
                    dim = layer.input_dim
                    if layer.name == "season_emb" or dim == 4: 
                        max_indices["season_seq"] = dim - 1
                    elif 15 <= dim <= 25: 
                        max_indices["country"] = dim - 1
                    elif 50 <= dim <= 100: 
                        max_indices["city"] = dim - 1
                    elif 8 <= dim <= 14: 
                        max_indices["disease"] = dim - 1

            for k in ["season_seq", "country", "city", "disease"]:
                # Map any out-of-bounds index (e.g. 10 for disease) to the maximum valid index (e.g. 8)
                input_dict[k] = np.clip(input_dict[k], 0, max_indices[k])
        except Exception:
            pass # Failsafe

        probs = np.mean([m.predict(input_dict, verbose=0).ravel() for m in self.lstm_models], axis=0)
        preds = (probs >= self.lstm_threshold).astype(int)

        out = pd.DataFrame({
            "city": [g[1] for g in rows["group"]],
            "disease": [g[2] for g in rows["group"]],
            "as_of_week": [str(pd.Timestamp(d).date()) for d in rows["as_of_date"]],
            "lstm_flag": preds.astype(bool),
            "lstm_probability": np.round(probs, 4),
        })
        return out

    # ------------------------------------------------------------------
    # Step 6: weekly IF/DBSCAN flags — Task4.ipynb aggregation rule
    # "flag a week if at least one visit that week was flagged" (sensitivity-favoring)
    # ------------------------------------------------------------------
    @staticmethod
    def _weekly_if_dbscan_flags(visit_df: pd.DataFrame) -> pd.DataFrame:
        visit_df = visit_df.copy()
        visit_df["VISIT_WEEK_START"] = visit_df["VISIT_DATE"].dt.to_period("W").apply(lambda r: r.start_time)
        out = visit_df.groupby(["CITY", "DISEASE", "VISIT_WEEK_START"]).agg(
            if_flag=("if_pred", "max"),
            dbscan_flag=("dbscan_pred", "max"),
        ).reset_index()
        out["as_of_week"] = out["VISIT_WEEK_START"].astype(str)
        return out

    # ------------------------------------------------------------------
    # THE public entry point
    # ------------------------------------------------------------------
    def full_pipeline(self, raw_visits_df: pd.DataFrame, progress_callback=None) -> dict:
        warn = PipelineWarnings()

        if progress_callback:
            progress_callback("Cleaning Data", 25, "Filling missing values and parsing dates...")
        visits = self._prepare_visits(raw_visits_df, warn)
        
        if progress_callback:
            progress_callback("Preparing Features", 35, "Running CASE_RATE_WINDOW feature engineering...")
        visits = self._add_visit_features(visits)
        
        if progress_callback:
            progress_callback("Running Isolation Forest", 45, "Executing Isolation Forest anomaly model...")
        visits = visits.reset_index(drop=True)
        iso_features = SYM_COLS + ["DAY_INDEX_NORM", "AGE_AT_VISIT_NORM",
                                    "COMORBIDITY_COUNT_NORM", "RECENT_CASE_COUNT_NORM"]
        X_iso = visits[iso_features].values
        raw_pred = self.if_model.predict(X_iso)
        visits["if_pred"] = (raw_pred == -1).astype(int)
        visits["if_score"] = self.if_model.decision_function(X_iso)
        
        if progress_callback:
            progress_callback("Running DBSCAN", 55, "Running DBSCAN density clustering per city group...")
        pca_cols = [f"pca_{i}" for i in range(8)]
        visits[pca_cols] = self.pca.transform(visits[SYM_COLS].values)
        dbscan_features = pca_cols + ["DAY_INDEX_NORM", "RECENT_CASE_COUNT_NORM"]

        scores = np.zeros(len(visits))
        eps, min_samples = self.dbscan_params["eps"], self.dbscan_params["min_samples"]
        for (_city, _disease), chunk in visits.groupby(["CITY", "DISEASE"]):
            X = chunk[dbscan_features].values
            if len(X) < min_samples:
                continue
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
            for lbl in set(labels) - {-1}:
                mask = labels == lbl
                cluster_burst = chunk.loc[chunk.index[mask], "RECENT_CASE_COUNT"].mean()
                scores[chunk.index[mask]] = cluster_burst
        visits["dbscan_score"] = scores
        visits["dbscan_pred"] = (visits["dbscan_score"] >= self.dbscan_threshold).astype(int)

        if progress_callback:
            progress_callback("Aggregating Weekly Data", 65, "Aggregating metrics and weekly growth rates...")
        weekly_flags = self._weekly_if_dbscan_flags(visits)
        weekly = self._aggregate_weekly(visits)
        
        if progress_callback:
            progress_callback("Running LSTM", 75, "Forecasting outbreak probabilities with LSTM ensemble...")
        lstm_feats = self._lstm_build_features(weekly, warn)
        lstm_preds = self._lstm_predict_latest_window(lstm_feats, warn)

        if progress_callback:
            progress_callback("Fusion Scoring", 85, "Combining model scores with fusion logic...")
        fused = weekly_flags.merge(
            lstm_preds, left_on=["CITY", "DISEASE", "as_of_week"],
            right_on=["city", "disease", "as_of_week"], how="left",
        )
        fused["lstm_flag"] = fused["lstm_flag"].fillna(False).astype(bool)
        fused["lstm_probability"] = fused["lstm_probability"].fillna(np.nan)
        fused["points"] = (
            fused["if_flag"].astype(int) * POINTS["if"]
            + fused["dbscan_flag"].astype(int) * POINTS["dbscan"]
            + fused["lstm_flag"].astype(int) * POINTS["lstm"]
        )
        fused["alert_level"] = fused["points"].apply(points_to_alert)

        results = fused[["CITY", "DISEASE", "as_of_week", "if_flag", "dbscan_flag",
                          "lstm_flag", "lstm_probability", "points", "alert_level"]].rename(
            columns={"CITY": "city", "DISEASE": "disease"}
        ).to_dict(orient="records")

        return {"alerts": results, "warnings": warn.__dict__, "visits": visits, "weekly": weekly}

