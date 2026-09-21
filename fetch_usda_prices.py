from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from usda_auth import validate_api_key
from usda_fertilizer import DEFAULT_OUTPUT, fetch_all_reports, merge_history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch USDA AMS fertilizer prices and append them to local history."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="How many days of USDA report history to request on each run (default: 60).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="CSV history file to update.",
    )
    return parser.parse_args()


def main() -> None:
    # Local .env should win over a stale shell/Codespaces environment variable.
    # GitHub Actions has no committed .env, so its USDA_API_KEY secret still works normally.
    load_dotenv(override=True)
    args = parse_args()

    api_key = os.getenv("USDA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "USDA_API_KEY is missing. Copy .env.example to .env and add your key, "
            "or set USDA_API_KEY in the environment."
        )

    session = requests.Session()
    validate_api_key(session, api_key)

    output = Path(args.output)
    fetched = fetch_all_reports(
        api_key=api_key,
        days=args.days,
        session=session,
    )
    history = merge_history(fetched, output)

    newest = history["Date"].max().date().isoformat() if not history.empty else "N/A"
    print(f"Fetched rows this run: {len(fetched):,}")
    print(f"History rows after dedupe: {len(history):,}")
    print(f"Latest USDA observation: {newest}")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
