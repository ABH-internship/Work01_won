from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "ai" / "models" / "quote_probability.pkl"


@lru_cache(maxsize=1)
def load_model() -> Any:
    with MODEL_PATH.open("rb") as file:
        model = pickle.load(file)

    if not hasattr(model, "predict_proba"):
        raise TypeError("quote probability model must support predict_proba")

    return model


def predict_quote_probability(values: dict[str, Any]) -> float:
    model = load_model()
    row = pd.DataFrame(
        [
            {
                "customer_grade": values["customer_grade"],
                "quote_stage": values["quote_stage"],
                "quantity": int(values["quantity"]),
                "estimated_amount": float(values["estimated_amount"]),
                "days_until_due": int(values["days_until_due"]),
            }
        ]
    )
    return float(model.predict_proba(row)[0][1])


def planning_probability(model_probability: float) -> float:
    return min(max(model_probability, 0.25) * 1.10, 1.0)
