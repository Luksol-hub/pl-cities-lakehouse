import pytest

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.ingestion.gus_bdl import SCHEMA
from pl_cities_lakehouse.transformations.silver_wages import silver_wages


def bronze(spark, rows):
    return spark.createDataFrame(rows, schema=SCHEMA)


def test_clean_wages_pass(spark):
    silver = silver_wages(bronze(spark, [("Kraków", 2024, 10455.44), ("Kraków", 2025, 11404.02)]))

    assert silver.columns == ["city", "year", "wage_pln"]
    assert silver.count() == 2


def test_zero_wage_stops_the_pipeline(spark):
    # GUS stores missing values as 0.0; if one slipped past the bronze filter, silver must catch it.
    rows = [("Kraków", 2024, 10455.44), ("Kraków", 2025, 0.0)]

    with pytest.raises(DataQualityError, match="wage_pln outside"):
        silver_wages(bronze(spark, rows))


def test_duplicated_year_stops_the_pipeline(spark):
    rows = [("Kraków", 2025, 11404.02), ("Kraków", 2025, 11000.0)]

    with pytest.raises(DataQualityError, match="duplicated keys"):
        silver_wages(bronze(spark, rows))
