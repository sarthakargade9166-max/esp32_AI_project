from __future__ import annotations

# imports
import logging
from pathlib import Path
from typing import Any, Optional, Union

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# paths
_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_MODEL_PATH = _MODULE_DIR / "models" / "model.pkl"
_DEFAULT_SCALER_PATH = _MODULE_DIR / "models" / "scaler.pkl"

_FALLBACK_MODEL_PATH = _MODULE_DIR / "model.pkl"
_FALLBACK_SCALER_PATH = _MODULE_DIR / "scaler.pkl"

FEATURE_NAMES = [
    "queue_count",
    "avg_service_time",
    "active_counters",
    "hour_of_day",
    "day_of_week",
]


# predictor
class QueuePredictor:
    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        scaler_path: Optional[Union[str, Path]] = None,
        auto_load: bool = True,
    ) -> None:
        self.model_path = self._resolve_path(model_path, _DEFAULT_MODEL_PATH, _FALLBACK_MODEL_PATH)
        self.scaler_path = self._resolve_path(scaler_path, _DEFAULT_SCALER_PATH, _FALLBACK_SCALER_PATH)

        self._model: Any = None
        self._scaler: Any = None
        self._is_loaded: bool = False

        if auto_load:
            self.load_model()

    # resolve
    @staticmethod
    def _resolve_path(custom_path: Optional[Union[str, Path]], default_path: Path, fallback_path: Path) -> Path:
        if custom_path is not None:
            return Path(custom_path)
        if default_path.exists():
            return default_path
        if fallback_path.exists():
            return fallback_path
        return default_path

    # status
    @property
    def is_ready(self) -> bool:
        return self._is_loaded and self._model is not None

    # load
    def load_model(self) -> bool:
        logger.info("Loading model from: %s", self.model_path)

        if not self.model_path.exists():
            logger.error("Model file not found: %s", self.model_path)
            self._is_loaded = False
            return False

        try:
            self._model = joblib.load(self.model_path)

            if self.scaler_path.exists():
                self._scaler = joblib.load(self.scaler_path)
            else:
                self._scaler = None

            self._is_loaded = True
            return True

        except Exception as exc:
            logger.exception("Failed to load prediction artifacts: %s", exc)
            self._model = None
            self._scaler = None
            self._is_loaded = False
            return False

    # predict
    def predict(self, features: Union[np.ndarray, pd.DataFrame, list[float], list[list[float]]]) -> Optional[float]:
        if not self.is_ready:
            return None

        try:
            formatted = self._preprocess_input(features)

            if self._scaler is not None:
                formatted = self._scaler.transform(formatted)

            raw_pred = self._model.predict(formatted)

            val = float(raw_pred[0]) if isinstance(raw_pred, (np.ndarray, list)) else float(raw_pred)
            return max(0.0, round(val, 2))

        except Exception as exc:
            logger.exception("Prediction failed: %s", exc)
            return None

    # preprocess
    def _preprocess_input(self, features: Union[np.ndarray, pd.DataFrame, list[float], list[list[float]]]) -> Union[pd.DataFrame, np.ndarray]:
        if isinstance(features, pd.DataFrame):
            return features[FEATURE_NAMES] if all(col in features.columns for col in FEATURE_NAMES) else features
        elif isinstance(features, (list, np.ndarray)):
            arr = np.array(features, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return pd.DataFrame(arr, columns=FEATURE_NAMES)
        else:
            raise TypeError(f"Unsupported features type: {type(features)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    predictor = QueuePredictor()

    if predictor.is_ready:
        test_features = [10, 7.5, 3, 14, 2]
        result = predictor.predict(test_features)
        print(f"Test input: {test_features}")
        print(f"Predicted wait time: {result} mins")
