"""Gold: yearly weather components of the quality of life index, per city.

Definitions (docs/quality-of-life-index.md):
- rainy day: precipitation of at least 1 mm,
- frost day: daily mean temperature below 0°C,
- hot day: daily mean temperature of at least 22°C.
Only full calendar years and the 17 ranked cities are kept; stadium towns used by
module B are left out.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

RAIN_MM = 1.0
FROST_C = 0.0
HOT_C = 22.0

# The weather data starts on 2006-07-01 and ends on 2026-06-30.
FIRST_FULL_YEAR = 2007
LAST_FULL_YEAR = 2025


def gold_weather_year(weather: DataFrame, cities: list[str]) -> DataFrame:
    """Count rainy, frost and hot days per city and full year from silver daily weather."""
    return (
        weather.filter(F.col("city").isin(cities))
        .withColumn("year", F.year("date"))
        .filter(F.col("year").between(FIRST_FULL_YEAR, LAST_FULL_YEAR))
        .groupBy("city", "year")
        .agg(
            F.count_if(F.col("precipitation_mm") >= RAIN_MM).alias("rainy_days"),
            F.count_if(F.col("temp_mean_c") < FROST_C).alias("frost_days"),
            F.count_if(F.col("temp_mean_c") >= HOT_C).alias("hot_days"),
        )
    )
