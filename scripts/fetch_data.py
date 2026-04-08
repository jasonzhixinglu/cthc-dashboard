"""Fetch raw public macro data for the CTHC China dashboard."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cthc.data_sources import TARGET_SERIES, fetch_all_series, get_source_registry


def main() -> None:
    """Run the raw data fetch pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--series",
        default=",".join(TARGET_SERIES),
        help="Comma-separated list of series to fetch.",
    )
    args = parser.parse_args()

    selected = [item.strip() for item in args.series.split(",") if item.strip()]
    registry = get_source_registry()
    print(f"[{timestamp()}] Starting fetch for {', '.join(selected)}")
    results = fetch_all_series(selected)

    success_count = 0
    fallback_count = 0
    for result in results:
        preferred_source = registry.get(result.series_name).preferred_source if result.series_name in registry else None
        if result.success and result.source_used == preferred_source:
            status = "success"
            success_count += 1
        elif result.success:
            status = "fallback"
            fallback_count += 1
            success_count += 1
        else:
            status = "failed"
        output = f" -> {result.output_path}" if result.output_path else ""
        print(f"[{status.upper():8}] {result.series_name:24} source={result.source_used:10} {result.message}{output}")

    print(
        f"[{timestamp()}] Completed fetch: {success_count}/{len(results)} succeeded, "
        f"{fallback_count} via fallback."
    )


def timestamp() -> str:
    """Return a compact UTC timestamp for logs."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    main()
