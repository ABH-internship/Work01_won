from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from statistics import mean


ROW_COUNT = 5000
RANDOM_SEED = 42
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "ai" / "data" / "quote_training_data.csv"

GRADES = ("A", "B", "C", "D")
STAGES = ("초기", "협의중", "유력")
FIELDNAMES = (
    "customer_grade",
    "quote_stage",
    "quantity",
    "estimated_amount",
    "days_until_due",
    "converted",
)


def conversion_probability(row: dict[str, object]) -> float:
    probability = 0.35

    probability += {"A": 0.25, "B": 0.08, "C": -0.06, "D": -0.18}[str(row["customer_grade"])]
    probability += {"초기": -0.18, "협의중": 0.05, "유력": 0.25}[str(row["quote_stage"])]

    quantity = int(row["quantity"])
    amount = int(row["estimated_amount"])
    days_until_due = int(row["days_until_due"])

    if days_until_due < 7:
        probability -= 0.15
    elif days_until_due <= 20:
        probability += 0.05
    else:
        probability -= 0.03

    if amount < 30_000_000:
        probability += 0.03
    elif amount <= 80_000_000:
        probability += 0.05
    else:
        probability -= 0.08

    if quantity <= 2:
        probability += 0.04
    elif quantity >= 5:
        probability -= 0.06

    return max(0.05, min(0.95, probability))


def generate_row(rng: random.Random) -> dict[str, object]:
    row: dict[str, object] = {
        "customer_grade": rng.choices(GRADES, weights=(0.25, 0.35, 0.25, 0.15), k=1)[0],
        "quote_stage": rng.choices(STAGES, weights=(0.30, 0.45, 0.25), k=1)[0],
        "quantity": rng.randint(1, 6),
        "estimated_amount": rng.randrange(18_000_000, 121_000_000, 1_000_000),
        "days_until_due": rng.randint(3, 35),
    }
    row["converted"] = int(rng.random() < conversion_probability(row))
    return row


def generate_rows(count: int, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    return [generate_row(rng) for _ in range(count)]


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, object]], output_path: Path) -> None:
    conversion_rate = mean(int(row["converted"]) for row in rows)

    print(f"created={output_path}")
    print(f"rows={len(rows)}")
    print(f"conversion_rate={conversion_rate:.3f}")

    for grade in GRADES:
        grade_rows = [row for row in rows if row["customer_grade"] == grade]
        rate = mean(int(row["converted"]) for row in grade_rows)
        print(f"grade_{grade}_count={len(grade_rows)} grade_{grade}_conversion_rate={rate:.3f}")

    for stage in STAGES:
        stage_rows = [row for row in rows if row["quote_stage"] == stage]
        rate = mean(int(row["converted"]) for row in stage_rows)
        print(f"stage_{stage}_count={len(stage_rows)} stage_{stage}_conversion_rate={rate:.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate quote conversion training data.")
    parser.add_argument("--rows", type=int, default=ROW_COUNT)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_rows(args.rows, args.seed)
    write_csv(rows, args.output)
    print_summary(rows, args.output)


if __name__ == "__main__":
    main()
