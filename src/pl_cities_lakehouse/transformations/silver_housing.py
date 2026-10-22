"""Silver: NBP housing prices per market, price type, city and quarter, checked for quality."""

from pyspark.sql import DataFrame

from pl_cities_lakehouse.common.quality import assert_quality

KEYS = ["market", "price_type", "city", "year", "quarter"]

# A price per m² outside this range would be a parsing error, not a market price
# (the real data spans roughly 1 900 to 19 000 PLN/m²).
RANGES = {
    "price_pln_m2": (500.0, 100_000.0),
    "quarter": (1, 4),
}


def silver_housing(bronze: DataFrame) -> DataFrame:
    """Return the checked prices; stop with DataQualityError if a rule is broken."""
    assert_quality(
        bronze, table="silver_housing", keys=KEYS, not_null=["price_pln_m2"], ranges=RANGES
    )
    return bronze.select(*KEYS, "price_pln_m2")
