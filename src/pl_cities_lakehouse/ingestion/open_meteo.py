"""Open-Meteo historical weather: download daily weather for project cities."""

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, DoubleType, StringType, StructField, StructType

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_METRICS = ["temperature_2m_mean", "precipitation_sum", "wind_speed_10m_max"]

# Same period as the NBP housing prices: Q3 2006 to Q2 2026.
START_DATE = "2006-07-01"
END_DATE = "2026-06-30"

# Incremental loading: the archive publishes a day with a delay of a few days, and values of the
# most recent days can still be corrected, so every run fetches the last week again.
ARCHIVE_DELAY_DAYS = 5
LOOKBACK_DAYS = 7

MAX_ATTEMPTS = 3

SOURCE = "open-meteo-archive"

SCHEMA = StructType(
    [
        StructField("city", StringType(), False),
        StructField("date", DateType(), False),
        StructField("temp_mean_c", DoubleType(), True),
        StructField("precipitation_mm", DoubleType(), True),
        StructField("wind_max_kmh", DoubleType(), True),
    ]
)

POLISH_TO_ASCII = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def city_slug(city: str) -> str:
    """File-safe city name: 'Zielona Góra' -> 'zielona_gora'."""
    return city.translate(POLISH_TO_ASCII).lower().replace(" ", "_")


def fetch_daily_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
    """Return the Open-Meteo archive response for one location as a dict."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_METRICS),
        "timezone": "Europe/Warsaw",
    }
    # The API sometimes fails for a moment (timeouts, empty bodies), so retry a few times.
    # 429 means we hit the per-minute rate limit, so wait for the next minute.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            if attempt == MAX_ATTEMPTS:
                raise
            rate_limited = error.response is not None and error.response.status_code == 429
            time.sleep(60 if rate_limited else 2**attempt)


def save_raw_responses(
    cities: dict[str, tuple[float, float]],
    out_dir: Path,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
) -> list[Path]:
    """Download weather for each city and save the API response as-is, one JSON file per city.

    Cities that already have a file are skipped, so a rerun only fetches what is missing.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for city, (latitude, longitude) in cities.items():
        path = out_dir / f"{city_slug(city)}.json"
        if not path.exists():
            response = fetch_daily_weather(latitude, longitude, start_date, end_date)
            path.write_text(json.dumps(response), encoding="utf-8")
        paths.append(path)
    return paths


def to_records(city: str, response: dict) -> list[dict]:
    """Turn the column lists of an API response into one record per day."""
    daily = response["daily"]
    records = []
    for day, temp, rain, wind in zip(
        daily["time"],
        daily["temperature_2m_mean"],
        daily["precipitation_sum"],
        daily["wind_speed_10m_max"],
        strict=True,
    ):
        records.append(
            {
                "city": city,
                "date": date.fromisoformat(day),
                "temp_mean_c": temp,
                "precipitation_mm": rain,
                "wind_max_kmh": wind,
            }
        )
    return records


def read_records(cities: dict[str, tuple[float, float]], raw_dir: Path) -> list[dict]:
    """Read the saved JSON file of each city and turn it into daily records."""
    records = []
    for city in cities:
        path = raw_dir / f"{city_slug(city)}.json"
        response = json.loads(path.read_text(encoding="utf-8"))
        records.extend(to_records(city, response))
    return records


def to_dataframe(spark: SparkSession, records: list[dict]) -> DataFrame:
    """Build the bronze DataFrame with load metadata."""
    return (
        spark.createDataFrame(records, schema=SCHEMA)
        .withColumn("source", F.lit(SOURCE))
        .withColumn("ingested_at", F.lit(datetime.now(timezone.utc)))
    )


def last_dates(bronze: DataFrame) -> dict[str, date]:
    """Last loaded day of each city in the bronze table."""
    rows = bronze.groupBy("city").agg(F.max("date").alias("last_date")).collect()
    return {row["city"]: row["last_date"] for row in rows}


def incremental_ranges(
    cities: dict[str, tuple[float, float]],
    loaded: dict[str, date],
    today: date,
    lookback_days: int = LOOKBACK_DAYS,
    delay_days: int = ARCHIVE_DELAY_DAYS,
) -> dict[str, tuple[date, date]]:
    """Date range to fetch for each city: from a week before its last loaded day
    (whole history for a new city) to the last day the archive already has."""
    end = today - timedelta(days=delay_days)
    ranges = {}
    for city in cities:
        last = loaded.get(city)
        if last is None:
            start = date.fromisoformat(START_DATE)
        else:
            start = last - timedelta(days=lookback_days - 1)
        if start <= end:
            ranges[city] = (start, end)
    return ranges


def save_increments(
    cities: dict[str, tuple[float, float]],
    ranges: dict[str, tuple[date, date]],
    out_dir: Path,
) -> list[tuple[str, Path]]:
    """Download each range and save it as `<city>_<start>_<end>.json`; returns (city, path) pairs.

    A file that already exists is not downloaded again, so a rerun on the same day is cheap.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for city, (start, end) in ranges.items():
        latitude, longitude = cities[city]
        path = out_dir / f"{city_slug(city)}_{start}_{end}.json"
        if not path.exists():
            response = fetch_daily_weather(latitude, longitude, start.isoformat(), end.isoformat())
            path.write_text(json.dumps(response), encoding="utf-8")
        saved.append((city, path))
    return saved


def read_increment_records(saved: list[tuple[str, Path]]) -> list[dict]:
    """Daily records from the files written by `save_increments`."""
    records = []
    for city, path in saved:
        response = json.loads(path.read_text(encoding="utf-8"))
        records.extend(to_records(city, response))
    return records
