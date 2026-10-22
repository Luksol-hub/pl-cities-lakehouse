import json
from datetime import date

import pytest
import requests

from pl_cities_lakehouse.ingestion import open_meteo
from pl_cities_lakehouse.ingestion.open_meteo import (
    SCHEMA,
    city_slug,
    fetch_daily_weather,
    read_records,
    save_raw_responses,
    to_dataframe,
    to_records,
)

# A tiny API response with the same shape as the real one: one list per metric.
RESPONSE = {
    "daily": {
        "time": ["2025-01-01", "2025-01-02"],
        "temperature_2m_mean": [3.4, 5.8],
        "precipitation_sum": [0.0, 6.5],
        "wind_speed_10m_max": [25.3, None],
    }
}

CITIES = {"Kraków": (50.06, 19.94), "Zielona Góra": (51.94, 15.51)}


class FakeResponse:
    """Stands in for requests.Response so tests do not call the real API."""

    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip the waiting between retries so tests run instantly."""
    monkeypatch.setattr(open_meteo.time, "sleep", lambda seconds: None)


def test_city_slug():
    assert city_slug("Zielona Góra") == "zielona_gora"
    assert city_slug("Łódź") == "lodz"
    assert city_slug("Kraków") == "krakow"


def test_to_records_one_row_per_day():
    records = to_records("Kraków", RESPONSE)

    assert records == [
        {
            "city": "Kraków",
            "date": date(2025, 1, 1),
            "temp_mean_c": 3.4,
            "precipitation_mm": 0.0,
            "wind_max_kmh": 25.3,
        },
        {
            "city": "Kraków",
            "date": date(2025, 1, 2),
            "temp_mean_c": 5.8,
            "precipitation_mm": 6.5,
            "wind_max_kmh": None,
        },
    ]


def test_to_records_fails_when_lists_differ_in_length():
    broken = {"daily": {**RESPONSE["daily"], "precipitation_sum": [0.0]}}

    with pytest.raises(ValueError):
        to_records("Kraków", broken)


def test_fetch_retries_after_temporary_error(monkeypatch, no_sleep):
    answers = [FakeResponse(status_code=500), FakeResponse(RESPONSE)]
    monkeypatch.setattr(open_meteo.requests, "get", lambda *args, **kwargs: answers.pop(0))

    assert fetch_daily_weather(50.06, 19.94, "2025-01-01", "2025-01-02") == RESPONSE


def test_fetch_gives_up_after_max_attempts(monkeypatch, no_sleep):
    monkeypatch.setattr(
        open_meteo.requests, "get", lambda *args, **kwargs: FakeResponse(status_code=429)
    )

    with pytest.raises(requests.HTTPError):
        fetch_daily_weather(50.06, 19.94, "2025-01-01", "2025-01-02")


def test_save_raw_responses_skips_existing_files(tmp_path, monkeypatch):
    (tmp_path / "krakow.json").write_text(json.dumps(RESPONSE), encoding="utf-8")
    fetched = []

    def fake_fetch(latitude, longitude, start_date, end_date):
        fetched.append((latitude, longitude))
        return RESPONSE

    monkeypatch.setattr(open_meteo, "fetch_daily_weather", fake_fetch)

    paths = save_raw_responses(CITIES, tmp_path)

    assert [p.name for p in paths] == ["krakow.json", "zielona_gora.json"]
    assert fetched == [(51.94, 15.51)], "only the missing city should be downloaded"


def test_read_records_and_dataframe(tmp_path, spark):
    for city in CITIES:
        (tmp_path / f"{city_slug(city)}.json").write_text(json.dumps(RESPONSE), encoding="utf-8")

    records = read_records(CITIES, tmp_path)
    df = to_dataframe(spark, records)

    assert {r["city"] for r in records} == {"Kraków", "Zielona Góra"}
    assert df.count() == 4
    assert df.columns == [*SCHEMA.fieldNames(), "source", "ingested_at"]
