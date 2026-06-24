"""
Unit tests for the FRED API ingest module.

These tests never hit the real FRED API — they mock the HTTP layer so they
run fast, offline, and safely in CI without needing a real API key.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pipeline.fred_ingest import FREDObservation, fetch_series


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(observations: list[dict], status_code: int = 200) -> MagicMock:
    """Build a fake requests.Response object."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"observations": observations}
    mock.raise_for_status.side_effect = None  # no-op for 200s
    return mock


def _mock_error_response(status_code: int) -> MagicMock:
    """Build a fake requests.Response that raises on raise_for_status."""
    from requests.exceptions import HTTPError
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = HTTPError(f"{status_code} Error")
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("pipeline.fred_ingest.requests.get")
def test_fetch_series_normal_observation(mock_get):
    """A standard observation with a real value parses correctly."""
    mock_get.return_value = _mock_response([
        {"date": "2024-01-02", "value": "3.91"},
    ])

    result = fetch_series("DGS10", api_key="fake-key")

    assert len(result) == 1
    obs = result[0]
    assert isinstance(obs, FREDObservation)
    assert obs.series_id == "DGS10"
    assert obs.series_name == "Treasury 10-Year"
    assert obs.observation_date == date(2024, 1, 2)
    assert obs.value == 3.91


@patch("pipeline.fred_ingest.requests.get")
def test_fetch_series_missing_value(mock_get):
    """FRED uses '.' for missing data — should coerce to None, not crash."""
    mock_get.return_value = _mock_response([
        {"date": "2024-01-01", "value": "."},  # New Year's Day
    ])

    result = fetch_series("DGS10", api_key="fake-key")

    assert len(result) == 1
    assert result[0].value is None
    assert result[0].observation_date == date(2024, 1, 1)


@patch("pipeline.fred_ingest.requests.get")
def test_fetch_series_http_error(mock_get):
    """A bad API response (e.g. invalid key, rate limit) should raise."""
    from requests.exceptions import HTTPError
    mock_get.return_value = _mock_error_response(400)

    with pytest.raises(HTTPError):
        fetch_series("DGS10", api_key="bad-key")
