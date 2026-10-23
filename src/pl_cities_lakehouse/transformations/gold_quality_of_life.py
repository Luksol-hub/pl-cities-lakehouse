"""Gold: quality of life index per city and year (docs/quality-of-life-index.md).

Each component is scaled to 0–1 within its year with inverted min-max scaling
(fewer bad days = better): the best city that year gets 1, the worst gets 0.
Index = 50% weather (rain 40%, frost 40%, heat 20%) + 50% air (PM10 smog days).
"""

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

WEATHER_WEIGHTS = {"rainy_days": 0.4, "frost_days": 0.4, "hot_days": 0.2}
WEATHER_SHARE = 0.5
AIR_SHARE = 0.5


def inverted_min_max(column: str, window: Window) -> Column:
    """(max - value) / (max - min) within the window; 1.0 when every city has the same value."""
    low = F.min(column).over(window)
    high = F.max(column).over(window)
    return F.when(high == low, F.lit(1.0)).otherwise((high - F.col(column)) / (high - low))


def gold_quality_of_life(weather_year: DataFrame, pm10: DataFrame) -> DataFrame:
    """Combine yearly weather counts and PM10 smog days into one index per city and year.

    The inner join drops a city in a year without PM10 data on purpose: an index built
    from half of its parts would not be comparable with the other cities.
    """
    components = weather_year.join(
        pm10.select("city", "year", "days_pm10_over_50"), on=["city", "year"], how="inner"
    )

    same_year = Window.partitionBy("year")
    scores = components
    for column in [*WEATHER_WEIGHTS, "days_pm10_over_50"]:
        scores = scores.withColumn(f"{column}_score", inverted_min_max(column, same_year))

    weather_score = sum(
        F.col(f"{column}_score") * weight for column, weight in WEATHER_WEIGHTS.items()
    )
    return (
        scores.withColumn("weather_score", weather_score)
        .withColumn("air_score", F.col("days_pm10_over_50_score"))
        .withColumn(
            "quality_of_life_index",
            WEATHER_SHARE * F.col("weather_score") + AIR_SHARE * F.col("air_score"),
        )
        .drop("days_pm10_over_50_score")
    )
