from __future__ import annotations

# imports
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_model")

# paths
_MODULE_DIR = Path(__file__).resolve().parent
_PRIMARY_MODEL_PATH = _MODULE_DIR / "models" / "model.pkl"
_PRIMARY_SCALER_PATH = _MODULE_DIR / "models" / "scaler.pkl"

_FALLBACK_MODEL_PATH = _MODULE_DIR / "model.pkl"
_FALLBACK_SCALER_PATH = _MODULE_DIR / "model.pkl"

# schema
FEATURE_NAMES = [
    "queue_count",
    "avg_service_time",
    "active_counters",
    "hour_of_day",
    "day_of_week",
]
EXPECTED_FEATURE_COUNT = len(FEATURE_NAMES)


# resolve
def resolve_artifact_path(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback


# test
def run_deployment_validation() -> bool:
    model_path = resolve_artifact_path(_PRIMARY_MODEL_PATH, _FALLBACK_MODEL_PATH)
    scaler_path = resolve_artifact_path(_PRIMARY_SCALER_PATH, _FALLBACK_SCALER_PATH)

    if not model_path.exists():
        logger.error("model.pkl not found")
        return False
    print(f"✓ model.pkl found ({model_path.name})")

    scaler_present = scaler_path.exists()
    if scaler_present:
        print(f"✓ scaler.pkl found ({scaler_path.name})")

    try:
        model = joblib.load(model_path)
        print("✓ model loaded")
    except Exception as exc:
        logger.error("Failed to load model: %s", exc)
        return False

    scaler = None
    if scaler_present:
        try:
            scaler = joblib.load(scaler_path)
            print("✓ scaler loaded")
        except Exception as exc:
            logger.error("Failed to load scaler: %s", exc)
            return False

    n_features_in = getattr(model, "n_features_in_", EXPECTED_FEATURE_COUNT)
    if n_features_in == EXPECTED_FEATURE_COUNT:
        print("✓ feature count matches")
    else:
        return False

    sample_raw = [10.0, 7.5, 3.0, 14.0, 2.0]
    sample_df = pd.DataFrame([sample_raw], columns=FEATURE_NAMES)

    try:
        sample_input = scaler.transform(sample_df) if scaler is not None else sample_df.to_numpy()
        pred_raw = model.predict(sample_input)
        val = float(pred_raw[0]) if isinstance(pred_raw, (np.ndarray, list)) else float(pred_raw)
        predicted_wait = max(0.0, round(val, 2))

        print("\n" + "=" * 50)
        print("✓ prediction successful")
        print(f"Predicted Waiting Time: {predicted_wait} minutes")
        print("=" * 50 + "\n")
        return True

    except Exception as exc:
        logger.exception("Prediction validation failed: %s", exc)
        return False


if __name__ == "__main__":
    if not run_deployment_validation():
        sys.exit(1)
