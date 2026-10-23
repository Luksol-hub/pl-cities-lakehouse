import pytest

from pl_cities_lakehouse.transformations.gold_match_weather import COLUMNS, gold_match_weather

SCHEMA = (
    "home_goals int, away_goals int, result string,"
    " temp_mean_c double, precipitation_mm double, wind_max_kmh double"
)


def summary(spark, rows):
    df = gold_match_weather(spark.createDataFrame(rows, SCHEMA))
    return df, {(r.factor, r.bucket): r for r in df.collect()}


def test_buckets_on_the_thresholds(spark):
    rows = [
        (1, 0, "H", 4.9, 0.9, 29.9),  # cold, dry, calm
        (1, 0, "H", 5.0, 1.0, 30.0),  # exactly on the lower bounds: mild, light, windy
        (1, 0, "H", 20.0, 5.0, 50.0),  # warm, heavy, stormy
    ]

    _, rows_by_bucket = summary(spark, rows)

    for bucket in [
        ("rain", "dry (< 1 mm)"),
        ("rain", "light (1-5 mm)"),
        ("rain", "heavy (>= 5 mm)"),
        ("temperature", "cold (< 5°C)"),
        ("temperature", "mild (5-20°C)"),
        ("temperature", "warm (>= 20°C)"),
        ("wind", "calm (< 30 km/h)"),
        ("wind", "windy (30-50 km/h)"),
        ("wind", "stormy (>= 50 km/h)"),
    ]:
        assert rows_by_bucket[bucket].matches == 1, bucket


def test_averages_and_result_shares(spark):
    # Three dry matches: a 3:1 home win, a 0:0 draw, a 1:2 away win.
    rows = [
        (3, 1, "H", 10.0, 0.0, 10.0),
        (0, 0, "D", 10.0, 0.0, 10.0),
        (1, 2, "A", 10.0, 0.0, 10.0),
    ]

    df, rows_by_bucket = summary(spark, rows)
    dry = rows_by_bucket[("rain", "dry (< 1 mm)")]

    assert df.columns == COLUMNS
    assert dry.matches == 3
    assert dry.avg_goals == pytest.approx(7 / 3)
    assert dry.avg_home_goal_diff == pytest.approx(1 / 3)  # (2 + 0 - 1) / 3
    assert (dry.home_win_share, dry.draw_share, dry.away_win_share) == pytest.approx(
        (1 / 3, 1 / 3, 1 / 3)
    )
