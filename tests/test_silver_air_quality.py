from pl_cities_lakehouse.ingestion.gios import SCHEMA
from pl_cities_lakehouse.transformations.silver_air_quality import silver_pm10


def bronze(spark, rows):
    """Build a small bronze table: (city, station, method, year, days over 50, completeness %)."""
    return spark.createDataFrame(rows, schema=SCHEMA)


def as_dict(df):
    """City and year -> (median days, number of stations), easy to compare in asserts."""
    return {(r.city, r.year): (r.days_pm10_over_50, r.stations) for r in df.collect()}


def test_drops_results_below_75_percent(spark):
    df = bronze(
        spark,
        [
            ("Kraków", "A", "24g", 2025, 20, 90.0),
            ("Kraków", "B", "24g", 2025, 99, 74.9),  # half-measured year: ignored
        ],
    )

    assert as_dict(silver_pm10(df)) == {("Kraków", 2025): (20.0, 1)}


def test_prefers_manual_method_when_station_has_both(spark):
    df = bronze(
        spark,
        [
            ("Kraków", "A", "1g", 2025, 32, 99.5),
            ("Kraków", "A", "24g", 2025, 25, 100.0),
        ],
    )

    assert as_dict(silver_pm10(df)) == {("Kraków", 2025): (25.0, 1)}


def test_falls_back_to_automatic_when_manual_incomplete(spark):
    df = bronze(
        spark,
        [
            ("Kraków", "A", "1g", 2025, 32, 99.5),
            ("Kraków", "A", "24g", 2025, 25, 50.0),  # manual too incomplete
        ],
    )

    assert as_dict(silver_pm10(df)) == {("Kraków", 2025): (32.0, 1)}


def test_median_over_stations(spark):
    df = bronze(
        spark,
        [
            # Odd number of stations: the middle value.
            ("Kraków", "A", "24g", 2025, 10, 100.0),
            ("Kraków", "B", "24g", 2025, 20, 100.0),
            ("Kraków", "C", "24g", 2025, 90, 100.0),
            # Even number of stations: the mean of the two middle values.
            ("Gdańsk", "D", "24g", 2025, 4, 100.0),
            ("Gdańsk", "E", "24g", 2025, 7, 100.0),
        ],
    )

    assert as_dict(silver_pm10(df)) == {
        ("Kraków", 2025): (20.0, 3),
        ("Gdańsk", 2025): (5.5, 2),
    }


def test_year_without_usable_station_has_no_row(spark):
    df = bronze(
        spark,
        [
            ("Opole", "A", "24g", 2007, 40, 60.0),
            ("Opole", "A", "24g", 2008, 45, 95.0),
        ],
    )

    assert as_dict(silver_pm10(df)) == {("Opole", 2008): (45.0, 1)}
