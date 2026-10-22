import pytest

from pl_cities_lakehouse.ingestion import gus_bdl
from pl_cities_lakehouse.ingestion.gus_bdl import (
    SCHEMA,
    fetch_variable,
    gus_unit_name,
    load_raw,
    save_raw,
    to_dataframe,
    to_records,
)

# Two of our cities, one powiat we do not use, and a missing value (attrId 91, stored as 0.0).
RESULTS = [
    {
        "id": "011212161000",
        "name": "Powiat m. Kraków",
        "values": [
            {"year": "2024", "val": 10455.44, "attrId": 1},
            {"year": "2025", "val": 11404.02, "attrId": 1},
        ],
    },
    {
        "id": "071412865000",
        "name": "Powiat m. st. Warszawa",
        "values": [
            {"year": "2024", "val": 0.0, "attrId": 91},
            {"year": "2025", "val": 11678.0, "attrId": 1},
        ],
    },
    {
        "id": "011200000000",
        "name": "Powiat wielicki",
        "values": [{"year": "2025", "val": 8000.0, "attrId": 1}],
    },
]


class FakeResponse:
    """Stands in for requests.Response so tests do not call the real API."""

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_gus_unit_name():
    assert gus_unit_name("Kraków") == "Powiat m. Kraków"
    assert gus_unit_name("Warszawa") == "Powiat m. st. Warszawa"


def test_fetch_variable_follows_all_pages(monkeypatch):
    pages = {
        "first": {"results": [RESULTS[0]], "links": {"next": "page-2"}},
        "page-2": {"results": [RESULTS[1]], "links": {"next": "page-3"}},
        "page-3": {"results": [RESULTS[2]], "links": {}},
    }

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(pages["first" if url.endswith("/64428") else url])

    monkeypatch.setattr(gus_bdl.requests, "get", fake_get)

    assert fetch_variable(64428) == RESULTS


def test_to_records_picks_our_cities_and_skips_missing_values():
    records = to_records(RESULTS, ["Kraków", "Warszawa"])

    assert records == [
        {"city": "Kraków", "year": 2024, "wage_pln": 10455.44},
        {"city": "Kraków", "year": 2025, "wage_pln": 11404.02},
        {"city": "Warszawa", "year": 2025, "wage_pln": 11678.0},
    ]


def test_to_records_fails_when_city_missing():
    with pytest.raises(ValueError, match="Gdańsk"):
        to_records(RESULTS, ["Kraków", "Gdańsk"])


def test_save_and_load_raw(tmp_path):
    path = save_raw(RESULTS, tmp_path / "gus" / "wages.json")

    assert load_raw(path) == RESULTS


def test_to_dataframe(spark):
    df = to_dataframe(spark, to_records(RESULTS, ["Kraków", "Warszawa"]))

    assert df.count() == 3
    assert df.columns == [*SCHEMA.fieldNames(), "source", "ingested_at"]
    assert df.select("source").distinct().collect()[0][0] == "gus-bdl-64428"
