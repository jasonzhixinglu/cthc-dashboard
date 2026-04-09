"""Run the fixed-parameter model and export frontend payload JSON files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.cthc.export_json import export_site_payload
from src.cthc.run_model import run_fixed_parameter_model


def main() -> None:
    """Parse arguments, run the model, and write site payload files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path, help="Path to the model input CSV file.")
    parser.add_argument(
        "--scenario",
        default="baseline",
        help="Scenario name to include in exported payloads.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/baseline.yaml"),
        help="Path to the fixed-parameter YAML config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("web/public/data"),
        help="Directory for frontend JSON payloads.",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input_csv)
    data["date"] = data["date"].str.replace(r"(\d{4})Q(\d)", r"\1-Q\2", regex=True)
    data = data.set_index("date")
    result = run_fixed_parameter_model(data, config_path=args.config)
    written_files = export_site_payload(
        result,
        output_dir=args.output_dir,
        scenario_name=args.scenario,
    )

    for filename, path in sorted(written_files.items()):
        print(f"{filename}: {path}")


if __name__ == "__main__":
    main()
