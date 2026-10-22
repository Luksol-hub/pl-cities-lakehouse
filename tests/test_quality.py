from datetime import date

import pytest

from pl_cities_lakehouse.common.quality import (
    DataQualityError,
    assert_quality,
    duplicate_keys,
    missing_days,
    null_values,
    out_of_range,
)

COLUMNS = ["city", "date", "value"]
SCHEMA = "city string, date date, value double"


@pytest.fixture
def clean(spark):
    """Two towns, three days each, nothing wrong."""
    rows = [
        ("Kraków", date(2025, 1, 1), 1.0),
        ("Kraków", date(2025, 1, 2), 2.0),
        ("Kraków", date(2025, 1, 3), 3.0),
        ("Gdańsk", date(2025, 1, 1), 4.0),
        ("Gdańsk", date(2025, 1, 2), 5.0),
        ("Gdańsk", date(2025, 1, 3), 6.0),
    ]
    return spark.createDataFrame(rows, COLUMNS)


def test_clean_data_passes_every_check(clean):
    assert duplicate_keys(clean, ["city", "date"]) == 0
    assert null_values(clean, "value") == 0
    assert out_of_range(clean, "value", 0, 10) == 0
    assert missing_days(clean, "city", "date") == {}
    assert_quality(clean, "t", keys=["city", "date"], not_null=["value"], ranges={"value": (0, 10)})


def test_duplicate_keys(spark, clean):
    duplicate = spark.createDataFrame([("Kraków", date(2025, 1, 2), 9.0)], COLUMNS)

    assert duplicate_keys(clean.union(duplicate), ["city", "date"]) == 1


def test_null_values(spark, clean):
    empty = spark.createDataFrame([("Kraków", date(2025, 1, 4), None)], SCHEMA)

    assert null_values(clean.union(empty), "value") == 1


def test_out_of_range_counts_both_ends_and_ignores_nulls(spark):
    rows = [
        ("A", date(2025, 1, 1), -1.0),
        ("A", date(2025, 1, 2), 11.0),
        ("A", date(2025, 1, 3), None),
    ]
    df = spark.createDataFrame(rows, SCHEMA)

    assert out_of_range(df, "value", 0, 10) == 2


def test_missing_days(clean):
    without_jan_2 = clean.filter("not (city = 'Kraków' and date = '2025-01-02')")

    assert missing_days(without_jan_2, "city", "date") == {"Kraków": 1}


def test_assert_quality_lists_every_problem(spark, clean):
    bad = spark.createDataFrame([("Kraków", date(2025, 1, 2), 99.0)], COLUMNS)

    with pytest.raises(DataQualityError) as error:
        assert_quality(clean.union(bad), "t", keys=["city", "date"], ranges={"value": (0, 10)})

    message = str(error.value)
    assert "1 duplicated keys" in message
    assert "1 values of value outside [0, 10]" in message
