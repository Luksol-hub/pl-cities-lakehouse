from datetime import date

import pytest

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.transformations.gold_dimensions import (
    OPEN_END,
    OPEN_START,
    dim_date,
    dim_location,
    dim_team,
    team_periods,
)
from pl_cities_lakehouse.transformations.gold_facts import fact_match, fact_wage

RELOCATIONS = [("Puszcza", date(2023, 7, 1), date(2025, 3, 1), "Kraków")]
TEAM_TOWNS = {"Puszcza": "Niepołomice", "Legia": "Warszawa"}


def test_team_periods_split_history_around_a_relocation():
    assert team_periods(TEAM_TOWNS, RELOCATIONS) == [
        ("Legia", "Warszawa", OPEN_START, OPEN_END),
        ("Puszcza", "Niepołomice", OPEN_START, date(2023, 6, 30)),
        ("Puszcza", "Kraków", date(2023, 7, 1), date(2025, 3, 1)),
        ("Puszcza", "Niepołomice", date(2025, 3, 2), OPEN_END),
    ]


def test_dim_team_marks_only_the_open_row_as_current(spark):
    rows = dim_team(spark, TEAM_TOWNS, RELOCATIONS).collect()

    current = {(r.team, r.home_town) for r in rows if r.is_current}
    assert current == {("Legia", "Warszawa"), ("Puszcza", "Niepołomice")}
    assert [r.team_key for r in rows] == [1, 2, 3, 4]


def test_dim_date_calendar_and_football_season(spark):
    rows = {r.date: r for r in dim_date(spark, date(2025, 6, 29), date(2025, 7, 1)).collect()}

    assert rows[date(2025, 6, 29)].date_key == 20250629
    assert rows[date(2025, 6, 29)].is_weekend  # Sunday
    assert rows[date(2025, 6, 30)].day_of_week == 1  # Monday
    assert rows[date(2025, 6, 30)].football_season == "2024/2025"
    assert rows[date(2025, 7, 1)].football_season == "2025/2026"


VOIVODESHIPS = {"Kraków": "małopolskie", "Niepołomice": "małopolskie", "Warszawa": "mazowieckie"}
WAGES_SCHEMA = "city string, year int, wage_pln double"


def locations(spark):
    return dim_location(
        spark,
        ranked={"Kraków": (50.06, 19.94)},
        stadium_towns={"Niepołomice": (50.04, 20.22), "Warszawa": (52.23, 21.01)},
        voivodeships=VOIVODESHIPS,
    )


def test_yearly_fact_points_to_first_day_of_year(spark):
    wages = spark.createDataFrame([("Kraków", 2025, 11404.02)], WAGES_SCHEMA)

    row = fact_wage(wages, locations(spark)).collect()[0]

    assert (row.location_key, row.date_key) == (1, 20250101)


def test_unknown_town_stops_the_pipeline(spark):
    wages = spark.createDataFrame([("Gdańsk", 2025, 11000.0)], WAGES_SCHEMA)

    with pytest.raises(DataQualityError, match="Gdańsk"):
        fact_wage(wages, locations(spark))


MATCH_SCHEMA = (
    "season string, match_date date, kickoff_time string, home_team string, away_team string,"
    " town string, home_goals int, away_goals int, result string,"
    " temp_mean_c double, precipitation_mm double, wind_max_kmh double"
)


def test_fact_match_uses_team_version_valid_on_match_day(spark):
    teams = dim_team(spark, TEAM_TOWNS, RELOCATIONS)
    keys = {(r.team, r.home_town, r.valid_from): r.team_key for r in teams.collect()}
    def match(season, day, town):
        return (season, day, "18:00", "Puszcza", "Legia", town, 1, 1, "D", 18.0, 0.0, 10.0)

    matches = spark.createDataFrame(
        [
            match("2023/2024", date(2023, 8, 7), "Kraków"),
            match("2024/2025", date(2025, 3, 2), "Niepołomice"),
        ],
        MATCH_SCHEMA,
    )

    rows = {r.date_key: r for r in fact_match(matches, locations(spark), teams).collect()}

    assert rows[20230807].home_team_key == keys[("Puszcza", "Kraków", date(2023, 7, 1))]
    assert rows[20250302].home_team_key == keys[("Puszcza", "Niepołomice", date(2025, 3, 2))]
    assert rows[20230807].away_team_key == keys[("Legia", "Warszawa", OPEN_START)]
