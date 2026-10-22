import pytest

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.ingestion.nbp_housing import SCHEMA
from pl_cities_lakehouse.transformations.silver_housing import KEYS, silver_housing

GOOD = [
    ("primary", "offer", "Kraków", 2026, 2, 16867.09),
    ("primary", "transaction", "Kraków", 2026, 2, 15922.88),
]


def bronze(spark, rows):
    return spark.createDataFrame(rows, schema=SCHEMA)


def test_clean_prices_pass(spark):
    silver = silver_housing(bronze(spark, GOOD))

    assert silver.columns == [*KEYS, "price_pln_m2"]
    assert silver.count() == 2


def test_duplicated_price_stops_the_pipeline(spark):
    rows = [*GOOD, ("primary", "offer", "Kraków", 2026, 2, 16000.0)]

    with pytest.raises(DataQualityError, match="duplicated keys"):
        silver_housing(bronze(spark, rows))


def test_impossible_price_stops_the_pipeline(spark):
    rows = [*GOOD, ("secondary", "offer", "Kraków", 2026, 2, 16.87)]  # PLN/m² lost a factor of 1000

    with pytest.raises(DataQualityError, match="price_pln_m2 outside"):
        silver_housing(bronze(spark, rows))
