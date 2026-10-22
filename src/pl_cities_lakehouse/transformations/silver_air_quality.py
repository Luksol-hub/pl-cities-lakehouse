"""Silver: PM10 smog days per city and year, from station-level bronze data.

Rules (docs/quality-of-life-index.md):
1. Use only station results with at least 75% of the year measured.
2. If a station measured with both methods, use the manual one ("24g", reference method);
   use the automatic one ("1g") only when the manual one is missing or incomplete.
3. The value for a city is the median over its stations.
A city and year with no usable station gets no row; gold decides how to treat the gap.
"""

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

MIN_COMPLETENESS_PCT = 75.0


def silver_pm10(bronze: DataFrame) -> DataFrame:
    """Return one row per city and year with the median number of days with PM10 over 50 µg/m³."""
    # 1. Keep only results that cover enough of the year.
    complete = bronze.filter(
        (F.col("completeness_pct") >= MIN_COMPLETENESS_PCT)
        & F.col("days_pm10_over_50").isNotNull()
    )

    # 2. One result per station and year: rank the methods and keep the best one.
    method_rank = F.when(F.col("averaging_time") == "24g", 1).otherwise(2)
    per_station = Window.partitionBy("city", "station_code", "year").orderBy(method_rank)
    one_per_station = (
        complete.withColumn("rank", F.row_number().over(per_station))
        .filter(F.col("rank") == 1)
        .drop("rank")
    )

    # 3. Median over the stations of each city.
    return one_per_station.groupBy("city", "year").agg(
        F.median("days_pm10_over_50").alias("days_pm10_over_50"),
        F.count("*").alias("stations"),
    )
