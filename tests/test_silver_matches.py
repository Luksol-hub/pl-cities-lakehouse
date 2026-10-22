from datetime import date

import pytest

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.ingestion.football import SCHEMA
from pl_cities_lakehouse.transformations.silver_matches import (
    MATCH_COLUMNS,
    WEATHER_COLUMNS,
    silver_matches,
)

WEATHER_SCHEMA = (
    "city string, date date, temp_mean_c double, precipitation_mm double, wind_max_kmh double"
)

WEATHER = [
    ("Szczecin", date(2012, 8, 17), 18.3, 1.2, 8.0),
    ("Zabrze", date(2025, 9, 1), 15.0, 7.5, 20.0),
]


def match(season, day, home, away, town, home_goals, away_goals, result):
    return (season, day, "18:00", home, away, town, home_goals, away_goals, result)


GOOD = [
    match("2012/2013", date(2012, 8, 17), "Pogon Szczecin", "Zaglebie", "Szczecin", 4, 0, "H"),
    match("2025/2026", date(2025, 9, 1), "Gornik Z.", "Wisla", "Zabrze", 1, 1, "D"),
]


def run(spark, matches, weather=WEATHER):
    return silver_matches(
        spark.createDataFrame(matches, schema=SCHEMA),
        spark.createDataFrame(weather, WEATHER_SCHEMA),
    )


def test_joins_match_day_weather(spark):
    silver = run(spark, GOOD)

    assert silver.columns == [*MATCH_COLUMNS, *WEATHER_COLUMNS]
    rows = {r.home_team: (r.temp_mean_c, r.precipitation_mm) for r in silver.collect()}
    assert rows == {"Pogon Szczecin": (18.3, 1.2), "Gornik Z.": (15.0, 7.5)}


def test_drops_seasons_without_full_weather(spark):
    current = match("2026/2027", date(2026, 10, 19), "Wisla Plock", "Radomiak", "Płock", 1, 0, "H")

    assert run(spark, [*GOOD, current]).count() == 2


def test_match_without_weather_stops_the_pipeline(spark):
    with pytest.raises(DataQualityError, match="1 matches without weather"):
        run(spark, GOOD, weather=WEATHER[:1])


def test_result_that_disagrees_with_goals_stops_the_pipeline(spark):
    draw_marked_as_home_win = match(
        "2025/2026", date(2025, 9, 1), "Gornik Z.", "Wisla", "Zabrze", 1, 1, "H"
    )
    wrong = [GOOD[0], draw_marked_as_home_win]

    with pytest.raises(DataQualityError, match="do not match the goals"):
        run(spark, wrong)


def test_two_home_matches_on_one_day_stops_the_pipeline(spark):
    twice = [*GOOD, match("2025/2026", date(2025, 9, 1), "Gornik Z.", "Legia", "Zabrze", 0, 2, "A")]

    with pytest.raises(DataQualityError, match="duplicated keys"):
        run(spark, twice)
