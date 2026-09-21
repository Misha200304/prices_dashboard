from __future__ import annotations

import requests

USDA_REPORTS_ENDPOINT = "https://marsapi.ams.usda.gov/services/v1.2/reports"


def validate_api_key(
    session: requests.Session,
    api_key: str,
    endpoint: str = USDA_REPORTS_ENDPOINT,
) -> None:
    """Validate MyMarketNews credentials before requesting individual reports."""
    response = session.get(
        endpoint,
        auth=(api_key.strip(), ""),
        timeout=30,
        headers={
            "Accept": "application/json",
            "User-Agent": "prices-dashboard/1.0",
        },
    )

    if response.status_code == 401:
        raise RuntimeError(
            "USDA API authentication failed (401 Unauthorized). "
            "USDA rejected USDA_API_KEY. Copy a fresh API key directly from "
            "MyMarketNews > My Profile > Show API key, and make sure .env "
            "contains only that key after USDA_API_KEY=."
        )

    response.raise_for_status()
