"""Gold: module B, how match-day weather relates to goals and home advantage.

Each match is put into a weather bucket for rain, temperature and wind. For every bucket we
count matches and compute average goals and the share of home wins, draws and away wins.
The table is long (one row per factor and bucket) so Power BI can show all factors with
one visual. Small buckets give noisy averages, so `matches` is kept to judge each result.
"""

from functools import reduce

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

# factor: (column, label of the lowest bucket, [(lower bound, label), ...] in ascending order)
BUCKETS = {
    "rain": (
        "precipitation_mm",
        "dry (< 1 mm)",
        [(1.0, "light (1-5 mm)"), (5.0, "heavy (>= 5 mm)")],
    ),
    "temperature": (
        "temp_mean_c",
        "cold (< 5°C)",
        [(5.0, "mild (5-20°C)"), (20.0, "warm (>= 20°C)")],
    ),
    "wind": (
        "wind_max_kmh",
        "calm (< 30 km/h)",
        [(30.0, "windy (30-50 km/h)"), (50.0, "stormy (>= 50 km/h)")],
    ),
}

COLUMNS = [
    "factor",
    "bucket",
    "bucket_order",
    "matches",
    "avg_goals",
    "avg_home_goal_diff",
    "home_win_share",
    "draw_share",
    "away_win_share",
]


def bucket(column: str, lowest: str, bounds: list[tuple[float, str]]) -> tuple[Column, Column]:
    """Bucket label and its position (1 = lowest, for sorting in Power BI) for each row."""
    label, order = F.lit(lowest), F.lit(1)
    for position, (lower, name) in enumerate(bounds, start=2):
        label = F.when(F.col(column) >= lower, name).otherwise(label)
        order = F.when(F.col(column) >= lower, position).otherwise(order)
    return label, order


def gold_match_weather(matches: DataFrame) -> DataFrame:
    """Summarise silver matches by weather bucket; one row per factor and bucket."""
    summaries = []
    for factor, (column, lowest, bounds) in BUCKETS.items():
        label, order = bucket(column, lowest, bounds)
        summaries.append(
            matches.withColumn("bucket", label)
            .withColumn("bucket_order", order)
            .groupBy("bucket", "bucket_order")
            .agg(
                F.count("*").alias("matches"),
                F.avg(F.col("home_goals") + F.col("away_goals")).alias("avg_goals"),
                F.avg(F.col("home_goals") - F.col("away_goals")).alias("avg_home_goal_diff"),
                F.avg((F.col("result") == "H").cast("double")).alias("home_win_share"),
                F.avg((F.col("result") == "D").cast("double")).alias("draw_share"),
                F.avg((F.col("result") == "A").cast("double")).alias("away_win_share"),
            )
            .withColumn("factor", F.lit(factor))
        )
    return reduce(DataFrame.unionByName, summaries).select(*COLUMNS)
