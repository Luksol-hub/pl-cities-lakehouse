"""Silver: GUS average monthly gross wage per city and year, checked for quality."""

from pyspark.sql import DataFrame

from pl_cities_lakehouse.common.quality import assert_quality

KEYS = ["city", "year"]

# GUS marks missing values with a code (filtered in bronze); a wage outside this range
# would mean such a value slipped through, e.g. the 0.0 stored for missing data.
RANGES = {"wage_pln": (500.0, 100_000.0)}


def silver_wages(bronze: DataFrame) -> DataFrame:
    """Return the checked wages; stop with DataQualityError if a rule is broken."""
    assert_quality(bronze, table="silver_wages", keys=KEYS, not_null=["wage_pln"], ranges=RANGES)
    return bronze.select(*KEYS, "wage_pln")
