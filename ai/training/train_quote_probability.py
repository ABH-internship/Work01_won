from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = BASE_DIR / "ai" / "data" / "quote_training_data.csv"
DEFAULT_MODEL_PATH = BASE_DIR / "ai" / "models" / "quote_probability.pkl"

CATEGORICAL_FEATURES = ["customer_grade", "quote_stage"]
NUMERIC_FEATURES = ["quantity", "estimated_amount", "days_until_due"]
TARGET = "converted"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("category", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("number", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )


def train(data_path: Path, model_path: Path) -> None:
    data = pd.read_csv(data_path)
    features = data[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    target = data[TARGET]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]

    accuracy = accuracy_score(y_test, predictions)
    roc_auc = roc_auc_score(y_test, probabilities)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as file:
        pickle.dump(pipeline, file)

    print(f"data={data_path}")
    print(f"model={model_path}")
    print(f"rows={len(data)}")
    print(f"accuracy={accuracy:.3f}")
    print(f"roc_auc={roc_auc:.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train quote conversion probability model.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train(args.data, args.model)


if __name__ == "__main__":
    main()
