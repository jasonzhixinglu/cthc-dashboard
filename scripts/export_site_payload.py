"""Run the fixed-parameter model and export frontend payload JSON files."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from src.cthc.export_json import export_site_payload
from src.cthc.run_model import run_fixed_parameter_model


def _archive_vintage(
    output_dir: Path,
    vintage_id: str,
    label: str,
    sample_end: str,
) -> None:
    """Copy current JSON/CSV outputs into a versioned vintage directory and update index.json."""
    vintages_dir = output_dir / "vintages"
    vintage_dir = vintages_dir / vintage_id
    vintage_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("summary.json", "series.json", "sectors.json", "cthc_estimates.csv"):
        src = output_dir / filename
        if src.exists():
            shutil.copy2(src, vintage_dir / filename)

    index_path = vintages_dir / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"vintages": []}

    vintages = index.get("vintages", [])
    new_entry = {
        "id": vintage_id,
        "label": label,
        "sample_end": sample_end,
        "data_path": f"vintages/{vintage_id}/",
    }
    # Replace any existing entry for the same date, then re-sort chronologically
    updated = [e for e in vintages if e.get("id") != vintage_id]
    updated.append(new_entry)
    updated.sort(key=lambda e: e["id"])
    index["vintages"] = updated

    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"vintages/index.json: {index_path}")
    print(f"vintages/{vintage_id}/: {vintage_dir}")


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
    parser.add_argument(
        "--no-vintage",
        action="store_true",
        help="Skip writing a new vintage archive entry.",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input_csv)
    data["date"] = data["date"].str.replace(r"(\d{4})Q(\d)", r"\1-Q\2", regex=True)
    data = data.set_index("date")

    gdp_valid = data["gdp"].dropna() if "gdp" in data.columns else pd.Series(dtype=float)
    display_end = str(gdp_valid.index[-1]) if not gdp_valid.empty else None

    result = run_fixed_parameter_model(data, config_path=args.config)
    written_files = export_site_payload(
        result,
        output_dir=args.output_dir,
        scenario_name=args.scenario,
        display_end=display_end,
    )

    for filename, path in sorted(written_files.items()):
        print(f"{filename}: {path}")

    if not args.no_vintage:
        today = date.today()
        vintage_id = today.strftime("%Y-%m-%d")
        label = today.strftime("%B %Y")
        sample_end = display_end or "n/a"
        _archive_vintage(args.output_dir, vintage_id, label, sample_end)


if __name__ == "__main__":
    main()
