"""Gold: mart_city_score, the city ranking that answers question A.

One row per market, city and year with both indices side by side, a 0–1 affordability score,
a final score (50% quality of life + 50% affordability) and the rank on each, where 1 is best.
Ranks and the affordability score are computed within the same year and market.
"""

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

QUALITY_OF_LIFE_SHARE = 0.5
AFFORDABILITY_SHARE = 0.5


def min_max(column: str, window: Window) -> Column:
    """(value - min) / (max - min) within the window, higher is better; 1.0 when all are equal."""
    low = F.min(column).over(window)
    high = F.max(column).over(window)
    return F.when(high == low, F.lit(1.0)).otherwise((F.col(column) - low) / (high - low))


def gold_city_score(quality_of_life: DataFrame, affordability: DataFrame) -> DataFrame:
    """Join the two indices and rank the cities within each year and market.

    The inner join keeps only cities that have a quality of life index in that year,
    so a city without PM10 data is left out of that year's ranking.
    """
    joined = affordability.select(
        "market", "city", "year", "avg_price_pln_m2", "wage_pln", "m2_per_wage"
    ).join(
        quality_of_life.select("city", "year", "quality_of_life_index"),
        on=["city", "year"],
        how="inner",
    )

    year_and_market = Window.partitionBy("year", "market")
    scored = joined.withColumn(
        "affordability_score", min_max("m2_per_wage", year_and_market)
    ).withColumn(
        "final_score",
        QUALITY_OF_LIFE_SHARE * F.col("quality_of_life_index")
        + AFFORDABILITY_SHARE * F.col("affordability_score"),
    )

    def rank_by(column: str) -> Column:
        return F.rank().over(year_and_market.orderBy(F.desc(column)))

    return (
        scored.withColumn("quality_of_life_rank", rank_by("quality_of_life_index"))
        .withColumn("affordability_rank", rank_by("m2_per_wage"))
        .withColumn("final_rank", rank_by("final_score"))
    )
