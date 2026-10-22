from datetime import date, datetime

import pytest

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.transformations.silver_weather import COLUMNS, silver_weather

BRONZE_SCHEMA = (
    "city string, date date, temp_mean_c double, precipitation_mm double, wind_max_kmh double,"
    " source string, ingested_at timestamp"
)
LOADED = datetime(2026, 10, 22, 12, 0)


def bronze(spark, rows):
    """Bronze weather rows: (city, date, temperature, rain, wind) plus load metadata."""
    return spark.createDataFrame(
        [(*row, "open-meteo-archive", LOADED) for row in rows], BRONZE_SCHEMA
    )


GOOD_DAYS = [
    ("Kraków", date(2025, 1, 1), 3.4, 0.0, 25.3),
    ("Kraków", date(2025, 1, 2), 5.8, 6.5, 29.9),
    ("Kraków", date(2025, 1, 3), -0.3, 0.3, 27.9),
]


def test_clean_weather_passes_and_drops_metadata(spark):
    silver = silver_weather(bronze(spark, GOOD_DAYS))

    assert silver.columns == COLUMNS
    assert silver.count() == 3


def test_impossible_temperature_stops_the_pipeline(spark):
    rows = [*GOOD_DAYS, ("Gdańsk", date(2025, 1, 1), 99.0, 0.0, 10.0)]

    with pytest.raises(DataQualityError, match="temp_mean_c outside"):
        silver_weather(bronze(spark, rows))


def test_duplicated_day_stops_the_pipeline(spark):
    rows = [*GOOD_DAYS, ("Kraków", date(2025, 1, 2), 5.8, 6.5, 29.9)]

    with pytest.raises(DataQualityError, match="duplicated keys"):
        silver_weather(bronze(spark, rows))


def test_missing_day_stops_the_pipeline(spark):
    rows = [GOOD_DAYS[0], GOOD_DAYS[2]]  # 2 January is missing

    with pytest.raises(DataQualityError, match="missing days"):
        silver_weather(bronze(spark, rows))


def test_empty_measurement_stops_the_pipeline(spark):
    rows = [*GOOD_DAYS[:2], ("Kraków", date(2025, 1, 3), None, 0.3, 27.9)]

    with pytest.raises(DataQualityError, match="empty values in temp_mean_c"):
        silver_weather(bronze(spark, rows))
