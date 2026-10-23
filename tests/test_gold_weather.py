from datetime import date

from pl_cities_lakehouse.transformations.gold_weather import gold_weather_year

SCHEMA = "city string, date date, temp_mean_c double, precipitation_mm double, wind_max_kmh double"


def counts(df):
    return {(r.city, r.year): (r.rainy_days, r.frost_days, r.hot_days) for r in df.collect()}


def test_counts_days_on_the_thresholds(spark):
    rows = [
        ("Kraków", date(2025, 1, 1), -0.1, 1.0, 10.0),  # frost and rain: exactly 1 mm counts
        ("Kraków", date(2025, 1, 2), 0.0, 0.9, 10.0),  # 0°C is not frost, 0.9 mm is not rain
        ("Kraków", date(2025, 7, 1), 22.0, 0.0, 10.0),  # exactly 22°C is a hot day
        ("Kraków", date(2025, 7, 2), 21.9, 5.0, 10.0),  # rain, not hot
    ]

    gold = gold_weather_year(spark.createDataFrame(rows, SCHEMA), ["Kraków"])

    assert counts(gold) == {("Kraków", 2025): (2, 1, 1)}


def test_keeps_only_ranked_cities_and_full_years(spark):
    rows = [
        ("Kraków", date(2006, 12, 31), -5.0, 0.0, 10.0),  # 2006 is not a full year
        ("Kraków", date(2007, 1, 1), -5.0, 0.0, 10.0),
        ("Kraków", date(2026, 1, 1), -5.0, 0.0, 10.0),  # 2026 is not a full year
        ("Gliwice", date(2007, 1, 1), -5.0, 0.0, 10.0),  # stadium town, not ranked
    ]

    gold = gold_weather_year(spark.createDataFrame(rows, SCHEMA), ["Kraków"])

    assert counts(gold) == {("Kraków", 2007): (0, 1, 0)}
