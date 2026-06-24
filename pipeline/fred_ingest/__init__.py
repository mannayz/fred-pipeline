"""
FRED API ingest module.

Fetches Treasury yield curve and SOFR rate series from the St. Louis Fed.
This is the entry point for all external data into the pipeline — validation
and coercion happen here, at the boundary, before anything else touches the data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import requests


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

IRR_SERIES = {
    "DGS1MO": "Treasury 1-Month",
    "DGS3MO": "Treasury 3-Month",
    "DGS6MO": "Treasury 6-Month",
    "DGS1":   "Treasury 1-Year",
    "DGS2":   "Treasury 2-Year",
    "DGS5":   "Treasury 5-Year",
    "DGS10":  "Treasury 10-Year",
    "DGS30":  "Treasury 30-Year",
    "SOFR":   "SOFR",
}


@dataclass
class FREDObservation:
    series_id: str
    series_name: str
    observation_date: date
    value: float | None  # None when FRED reports missing data as "."


def fetch_series(
    series_id: str,
    api_key: str,
    observation_start: str = "2020-01-01",
) -> list[FREDObservation]:
    response = requests.get(
        FRED_BASE_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": observation_start,
        },
        timeout=30,
    )
    response.raise_for_status()

    series_name = IRR_SERIES.get(series_id, series_id)
    observations = []

    for obs in response.json()["observations"]:
        raw_value = obs["value"]
        observations.append(
            FREDObservation(
                series_id=series_id,
                series_name=series_name,
                observation_date=date.fromisoformat(obs["date"]),
                value=float(raw_value) if raw_value != "." else None,
            )
        )

    return observations


def fetch_all_irr_series(
    api_key: str,
    observation_start: str = "2020-01-01",
) -> dict[str, list[FREDObservation]]:
    return {
        series_id: fetch_series(series_id, api_key, observation_start)
        for series_id in IRR_SERIES
    }
