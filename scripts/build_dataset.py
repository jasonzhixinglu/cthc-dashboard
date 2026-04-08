"""Build the quarterly model-ready dataset for the CTHC dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cthc.transforms import PROCESSED_DATA_PATH, build_model_dataset, summarize_dataset


def main() -> None:
    """Run the quarterly transformation pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DATA_PATH,
        help="Output CSV path for the processed quarterly dataset.",
    )
    args = parser.parse_args()

    dataset = build_model_dataset(output_path=args.output)
    summary = summarize_dataset(dataset)

    print(f"Output: {args.output}")
    print(f"Sample start: {summary['sample_start']}")
    print(f"Sample end: {summary['sample_end']}")
    print(f"Quarterly observations: {summary['observations']}")
    print("Missing values by column:")
    for column, missing in summary["missing_by_column"].items():
        print(f"  {column}: {missing}")


if __name__ == "__main__":
    main()
