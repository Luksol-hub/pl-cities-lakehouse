import openpyxl
import pytest

from pl_cities_lakehouse.ingestion import gios
from pl_cities_lakehouse.ingestion.gios import (
    METADATA_FILE,
    SCHEMA,
    STATISTICS_FILE,
    column_index,
    pm10_records,
    read_records,
    station_cities,
    to_dataframe,
)

# STACJE sheet: a Kraków station renamed over the years, a Gdańsk station, one in a town we skip.
METADATA_ROWS = [
    ("Nr", "Kod stacji", "Stary Kod stacji \n(o ile inny od aktualnego)", "Miejscowość"),
    (1, "MpKrakBujaka", "MpKrakowBuja, MpKrak6117", "Kraków"),
    (2, "PmGdaLeczkow", None, "Gdańsk"),
    (3, "MpSkawOgro", None, "Skawina"),
]

# PM10 sheet: header, units row, then data. The renamed station appears under its old code in 2007
# and with both measuring methods in 2025.
PM10_ROWS = [
    ("Rok", "Kod stacji", "Czas uśredniania", "L>50 (S24)", "Kompletność "),
    ("(-)", "(-)", "(-)", "(-)", "[%]"),
    (2007, "MpKrakowBuja", "24g", 157.0, 95.0),
    (2025, "MpKrakBujaka", "1g", 32, 99.5),
    (2025, "MpKrakBujaka", "24g", 25, 100),
    (2025, "PmGdaLeczkow", "1g", 5, 60),
    (2025, "MpSkawOgro", "24g", 40, 98),
]

CITIES = ["Kraków", "Gdańsk"]


def test_column_index_ignores_stray_spaces():
    header = PM10_ROWS[0]

    assert column_index(header, "Kompletność") == 4
    assert column_index(header, "L>50") == 3


def test_column_index_fails_when_column_missing():
    with pytest.raises(ValueError, match="Rok"):
        column_index(("Kod stacji",), "Rok")


def test_station_cities_includes_old_codes():
    mapping = station_cities(METADATA_ROWS, CITIES)

    assert mapping == {
        "MpKrakBujaka": "Kraków",
        "MpKrakowBuja": "Kraków",
        "MpKrak6117": "Kraków",
        "PmGdaLeczkow": "Gdańsk",
    }


def test_pm10_records_keeps_station_year_and_method():
    records = pm10_records(PM10_ROWS, station_cities(METADATA_ROWS, CITIES))

    assert records == [
        {
            "city": "Kraków",
            "station_code": "MpKrakowBuja",
            "averaging_time": "24g",
            "year": 2007,
            "days_pm10_over_50": 157,
            "completeness_pct": 95.0,
        },
        {
            "city": "Kraków",
            "station_code": "MpKrakBujaka",
            "averaging_time": "1g",
            "year": 2025,
            "days_pm10_over_50": 32,
            "completeness_pct": 99.5,
        },
        {
            "city": "Kraków",
            "station_code": "MpKrakBujaka",
            "averaging_time": "24g",
            "year": 2025,
            "days_pm10_over_50": 25,
            "completeness_pct": 100.0,
        },
        {
            "city": "Gdańsk",
            "station_code": "PmGdaLeczkow",
            "averaging_time": "1g",
            "year": 2025,
            "days_pm10_over_50": 5,
            "completeness_pct": 60.0,
        },
    ]


def write_workbook(path, sheet, rows):
    workbook = openpyxl.Workbook()
    workbook.active.title = sheet
    for row in rows:
        workbook.active.append(list(row))
    workbook.save(path)


def test_read_records_from_workbooks(tmp_path):
    write_workbook(tmp_path / METADATA_FILE, "STACJE", METADATA_ROWS)
    write_workbook(tmp_path / STATISTICS_FILE, "PM10", PM10_ROWS)

    records = read_records(tmp_path, CITIES)

    assert len(records) == 4
    assert {r["city"] for r in records} == {"Kraków", "Gdańsk"}


def test_download_skips_existing_files(tmp_path, monkeypatch):
    (tmp_path / STATISTICS_FILE).write_bytes(b"already here")
    requested = []

    class FakeResponse:
        content = b"new file"

        def raise_for_status(self):
            pass

    def fake_get(url, timeout=None):
        requested.append(url)
        return FakeResponse()

    monkeypatch.setattr(gios.requests, "get", fake_get)

    gios.download(tmp_path)

    assert requested == [gios.DOWNLOAD_URL.format(file_id=643)]
    assert (tmp_path / STATISTICS_FILE).read_bytes() == b"already here"
    assert (tmp_path / METADATA_FILE).read_bytes() == b"new file"


def test_to_dataframe(spark):
    records = pm10_records(PM10_ROWS, station_cities(METADATA_ROWS, CITIES))

    df = to_dataframe(spark, records)

    assert df.count() == 4
    assert df.columns == [*SCHEMA.fieldNames(), "source_file", "ingested_at"]
