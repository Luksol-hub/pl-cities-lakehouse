"""Gold: housing affordability per market, city and year (docs/quality-of-life-index.md).

m² per wage = average monthly gross wage / average transaction price per m² in the year,
read as "how many m² of a flat one average monthly wage buys". Higher is better.
Computed separately for the primary and secondary market; Power BI chooses or averages them.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

FIRST_YEAR = 2007
LAST_YEAR = 2025


def gold_affordability(housing: DataFrame, wages: DataFrame) -> DataFrame:
    """Join yearly average transaction prices with wages; one row per market, city and year."""
    yearly_prices = (
        housing.filter(F.col("price_type") == "transaction")
        .filter(F.col("year").between(FIRST_YEAR, LAST_YEAR))
        .groupBy("market", "city", "year")
        .agg(
            F.avg("price_pln_m2").alias("avg_price_pln_m2"),
            # Almost every year has 4 quarters; keeping the count shows when it does not.
            F.count("*").alias("quarters"),
        )
    )
    return yearly_prices.join(wages, on=["city", "year"], how="inner").withColumn(
        "m2_per_wage", F.col("wage_pln") / F.col("avg_price_pln_m2")
    )
