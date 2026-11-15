"""Fit every built model from data/raw/ and print how it scored.

    python -m ignis_ml.train

Nothing is written to disk: the models are small enough to fit on first use,
so this is for looking at the evaluation, not for producing a file.
"""

from __future__ import annotations

from .api import model_cards


def main() -> None:
    for card in model_cards():
        if card.status != "available":
            print(f"{card.model_id}: not built yet\n")
            continue
        table = card.trained_on[0]
        print(f"{card.model_id} (version {card.version})")
        print(f"  trained on  {table.psi_id}, {table.file_name}, {table.n_rows} rows, doi {table.doi}")
        print(f"  validation  {card.cv_scheme}")
        for metric in card.evaluation:
            print(f"  {metric.name:<32} {metric.value:8.4f}   {metric.baseline_name}: {metric.baseline_value:.4f}")
        for feature in card.features:
            tested = feature.categories or f"{feature.tested_min:g} to {feature.tested_max:g} {feature.unit}"
            print(f"  input  {feature.name:<22} {tested}")
        print(f"  notes  {card.notes}\n")


if __name__ == "__main__":
    main()
