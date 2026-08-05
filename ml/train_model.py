from __future__ import annotations

# imports
import argparse
import logging
import sys
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# paths
_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_CSV = _MODULE_DIR / "queue_data.csv"
_MODELS_DIR = _MODULE_DIR / "models"
_MODEL_PATH = _MODELS_DIR / "model.pkl"
_SCALER_PATH = _MODELS_DIR / "scaler.pkl"

# schema
FEATURE_COLUMNS = [
    "queue_count",
    "avg_service_time",
    "active_counters",
    "hour_of_day",
    "day_of_week",
]
TARGET_COLUMN = "actual_wait"

RANDOM_STATE = 42
TEST_SIZE = 0.20
VAL_SIZE = 0.20


# load
def load_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV is empty: {csv_path}")

    logger.info("Loaded %d rows from %s", len(df), csv_path.name)
    return df


# clean
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    required = FEATURE_COLUMNS + [TARGET_COLUMN]
    df = df[required].copy()

    df.dropna(inplace=True)
    df = df[df[TARGET_COLUMN] >= 0]
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info("Clean dataset size: %d rows", len(df))
    return df


# split
def split_data(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=VAL_SIZE, random_state=RANDOM_STATE
    )

    return X_train, X_val, X_test, y_train, y_val, y_test


# scale
def fit_scaler(X_train: pd.DataFrame) -> Tuple[StandardScaler, np.ndarray]:
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    return scaler, X_train_scaled


# train
def train_model(X_train: np.ndarray, y_train: pd.Series) -> RandomForestRegressor:
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    logger.info("Training RandomForestRegressor...")
    model.fit(X_train, y_train)
    return model


# evaluate
def evaluate(
    model: RandomForestRegressor,
    X: np.ndarray,
    y: pd.Series,
    split_name: str,
) -> dict[str, float]:
    predictions = model.predict(X)
    mae = mean_absolute_error(y, predictions)
    rmse = float(np.sqrt(mean_squared_error(y, predictions)))
    r2 = r2_score(y, predictions)

    logger.info("[%s] MAE: %.4f | RMSE: %.4f | R²: %.4f", split_name, mae, rmse, r2)
    return {"mae": mae, "rmse": rmse, "r2": r2}


# save
def save_artifacts(model: RandomForestRegressor, scaler: StandardScaler) -> None:
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, _MODEL_PATH)
    joblib.dump(scaler, _SCALER_PATH)
    logger.info("Saved model and scaler artifacts.")


# pipeline
def run_pipeline(csv_path: Path | None = None) -> None:
    csv_path = csv_path or _DEFAULT_CSV
    df = clean_data(load_csv(csv_path))

    X_train, X_val, X_test, y_train, y_val, y_test = split_data(df)

    scaler, X_train_scaled = fit_scaler(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    model = train_model(X_train_scaled, y_train)

    evaluate(model, X_train_scaled, y_train, "Train")
    evaluate(model, X_val_scaled, y_val, "Validation")
    evaluate(model, X_test_scaled, y_test, "Test")

    save_artifacts(model, scaler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RandomForest model.")
    parser.add_argument("--csv", type=Path, default=None, help="Path to input CSV")
    args = parser.parse_args()

    try:
        run_pipeline(csv_path=args.csv)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        sys.exit(1)