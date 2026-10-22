"""Silver: daily weather per town, checked for duplicates, gaps and impossible values.

The yearly counts used in the quality of life index (rainy, frosty and hot days) are
computed in gold; silver keeps one clean row per town and day.
"""

from pyspark.sql import DataFrame

from pl_cities_lakehouse.common.quality import DataQualityError, assert_quality, missing_days

# Physically plausible limits for Poland; a value outside means broken data, not weather.
RANGES = {
    "temp_mean_c": (-40.0, 45.0),
    "precipitation_mm": (0.0, 300.0),
    "wind_max_kmh": (0.0, 250.0),
}

COLUMNS = ["city", "date", "temp_mean_c", "precipitation_mm", "wind_max_kmh"]


def silver_weather(bronze: DataFrame) -> DataFrame:
    """Return the checked daily weather; stop with DataQualityError if a rule is broken."""
    assert_quality(
        bronze,
        table="silver_weather",
        keys=["city", "date"],
        not_null=["temp_mean_c", "precipitation_mm", "wind_max_kmh"],
        ranges=RANGES,
    )

    gaps = missing_days(bronze, group="city", date_column="date")
    if gaps:
        raise DataQualityError(f"silver_weather: missing days per town {gaps}")

    return bronze.select(*COLUMNS)
