import pytest

from pl_cities_lakehouse.transformations.gold_quality_of_life import gold_quality_of_life

WEATHER_SCHEMA = "city string, year int, rainy_days long, frost_days long, hot_days long"
PM10_SCHEMA = "city string, year int, days_pm10_over_50 double, stations long"


def run(spark, weather_rows, pm10_rows):
    return gold_quality_of_life(
        spark.createDataFrame(weather_rows, WEATHER_SCHEMA),
        spark.createDataFrame(pm10_rows, PM10_SCHEMA),
    )


def by_city(df):
    return {r.city: r for r in df.collect()}


def test_best_city_gets_1_worst_gets_0_middle_in_between(spark):
    weather = [
        ("A", 2025, 120, 30, 10),  # best in everything
        ("B", 2025, 130, 40, 15),  # exactly in the middle
        ("C", 2025, 140, 50, 20),  # worst in everything
    ]
    pm10 = [("A", 2025, 5.0, 1), ("B", 2025, 15.0, 1), ("C", 2025, 25.0, 1)]

    rows = by_city(run(spark, weather, pm10))

    assert rows["A"].quality_of_life_index == pytest.approx(1.0)
    assert rows["B"].quality_of_life_index == pytest.approx(0.5)
    assert rows["C"].quality_of_life_index == pytest.approx(0.0)


def test_weights_40_40_20_and_50_50(spark):
    # A is best on rain and frost but worst on heat and smog; B is the opposite.
    weather = [("A", 2025, 100, 10, 30), ("B", 2025, 200, 20, 10)]
    pm10 = [("A", 2025, 50.0, 1), ("B", 2025, 10.0, 1)]

    rows = by_city(run(spark, weather, pm10))

    assert rows["A"].weather_score == pytest.approx(0.8)  # 0.4 + 0.4 + 0
    assert rows["A"].air_score == pytest.approx(0.0)
    assert rows["A"].quality_of_life_index == pytest.approx(0.4)  # 0.5 * 0.8 + 0.5 * 0
    assert rows["B"].quality_of_life_index == pytest.approx(0.6)  # 0.5 * 0.2 + 0.5 * 1


def test_scaling_is_done_within_each_year(spark):
    # 2010 was cold everywhere: A has more frost days in 2010 than B in 2011,
    # but within its own year A is still the best.
    weather = [
        ("A", 2010, 100, 90, 10),
        ("B", 2010, 100, 99, 10),
        ("A", 2011, 100, 40, 10),
        ("B", 2011, 100, 30, 10),
    ]
    pm10 = [(c, y, 10.0, 1) for c in "AB" for y in (2010, 2011)]

    rows = {(r.city, r.year): r.frost_days_score for r in run(spark, weather, pm10).collect()}

    assert rows[("A", 2010)] == pytest.approx(1.0)
    assert rows[("B", 2011)] == pytest.approx(1.0)


def test_equal_values_score_1_instead_of_dividing_by_zero(spark):
    weather = [("A", 2025, 120, 30, 10), ("B", 2025, 120, 30, 10)]
    pm10 = [("A", 2025, 5.0, 1), ("B", 2025, 5.0, 1)]

    rows = by_city(run(spark, weather, pm10))

    assert rows["A"].quality_of_life_index == pytest.approx(1.0)


def test_city_without_pm10_in_a_year_is_left_out(spark):
    weather = [("Opole", 2007, 130, 40, 15), ("Kraków", 2007, 140, 44, 15)]
    pm10 = [("Kraków", 2007, 157.0, 3)]

    assert set(by_city(run(spark, weather, pm10))) == {"Kraków"}
