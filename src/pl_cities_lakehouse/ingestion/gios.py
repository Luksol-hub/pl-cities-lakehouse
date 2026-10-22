"""GIOŚ air quality: yearly PM10 statistics per measuring station.

GIOŚ publishes two workbooks in its measurement data bank:
- yearly statistics for every station, with a PM10 sheet that already counts
  days with a daily mean above 50 µg/m³ (column "L>50 (S24)"),
- station metadata, with the town of each station and its older codes.

Bronze keeps one row per station and year, as in the source. Filtering by
completeness and combining stations into one value per city happen in silver.
"""

from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import requests
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

STATISTICS_FILE = "Statystyki z lat 2000-2025.xlsx"
METADATA_FILE = "Metadane oraz kody stacji i stanowisk pomiarowych.xlsx"

# Download links from https://powietrze.gios.gov.pl/pjp/archives ("Bank danych pomiarowych").
# GIOŚ publishes a new statistics file every year, so the file id and name will change.
DOWNLOAD_URL = "https://powietrze.gios.gov.pl/pjp/archives/downloadFile/{file_id}"
FILE_IDS = {STATISTICS_FILE: 642, METADATA_FILE: 643}

SCHEMA = StructType(
    [
        StructField("city", StringType(), False),
        StructField("station_code", StringType(), False),
        StructField("averaging_time", StringType(), False),
        StructField("year", IntegerType(), False),
        StructField("days_pm10_over_50", IntegerType(), True),
        StructField("completeness_pct", DoubleType(), True),
    ]
)


def download(raw_dir: Path) -> list[Path]:
    """Download both GIOŚ workbooks into `raw_dir`, skipping files that are already there."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, file_id in FILE_IDS.items():
        path = raw_dir / name
        if not path.exists():
            response = requests.get(DOWNLOAD_URL.format(file_id=file_id), timeout=120)
            response.raise_for_status()
            path.write_bytes(response.content)
        paths.append(path)
    return paths


def column_index(header: tuple, name: str) -> int:
    """Position of a column whose header starts with `name` (headers have stray spaces)."""
    for i, value in enumerate(header):
        if isinstance(value, str) and value.strip().startswith(name):
            return i
    raise ValueError(f"Column {name!r} not found in header: {header}")


def station_cities(rows: list[tuple], cities: list[str]) -> dict[str, str]:
    """Map station codes (current and old ones) to our cities, from the STACJE sheet."""
    header = rows[0]
    code_col = column_index(header, "Kod stacji")
    old_col = column_index(header, "Stary Kod stacji")
    town_col = column_index(header, "Miejscowość")

    mapping = {}
    for row in rows[1:]:
        town = row[town_col]
        if town not in cities:
            continue
        mapping[row[code_col]] = town
        # A station renamed over the years lists its old codes, separated by commas.
        for old_code in str(row[old_col] or "").replace(",", " ").split():
            mapping[old_code] = town
    return mapping


def pm10_records(rows: list[tuple], stations: dict[str, str]) -> list[dict]:
    """One record per station and year for stations in our cities, from the PM10 sheet."""
    header = rows[0]
    year_col = column_index(header, "Rok")
    code_col = column_index(header, "Kod stacji")
    averaging_col = column_index(header, "Czas uśredniania")
    days_col = column_index(header, "L>50")
    completeness_col = column_index(header, "Kompletność")

    records = []
    # Row 1 holds units like "[µg/m3]", data starts at row 2.
    for row in rows[2:]:
        code = row[code_col]
        if code not in stations or not isinstance(row[year_col], int):
            continue
        records.append(
            {
                "city": stations[code],
                "station_code": code,
                # "24g": manual 24-hour sampling (reference method), "1g": automatic hourly monitor.
                # Some stations run both, so a station can have two rows in one year.
                "averaging_time": row[averaging_col],
                "year": row[year_col],
                "days_pm10_over_50": as_int(row[days_col]),
                "completeness_pct": as_float(row[completeness_col]),
            }
        )
    return records


def as_int(value) -> int | None:
    """Excel stores counts as numbers, sometimes with a decimal part; keep empty cells empty."""
    return None if value is None else int(value)


def as_float(value) -> float | None:
    return None if value is None else float(value)


def read_records(raw_dir: Path, cities: list[str]) -> list[dict]:
    """Read both GIOŚ workbooks and return PM10 records for our cities."""
    metadata = openpyxl.load_workbook(raw_dir / METADATA_FILE, read_only=True, data_only=True)
    statistics = openpyxl.load_workbook(raw_dir / STATISTICS_FILE, read_only=True, data_only=True)
    try:
        stations = station_cities(list(metadata["STACJE"].iter_rows(values_only=True)), cities)
        return pm10_records(list(statistics["PM10"].iter_rows(values_only=True)), stations)
    finally:
        metadata.close()
        statistics.close()


def to_dataframe(spark: SparkSession, records: list[dict]) -> DataFrame:
    """Build the bronze DataFrame with load metadata."""
    return (
        spark.createDataFrame(records, schema=SCHEMA)
        .withColumn("source_file", F.lit(STATISTICS_FILE))
        .withColumn("ingested_at", F.lit(datetime.now(timezone.utc)))
    )
