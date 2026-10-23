"""Gold: dimension tables of the star schema (dim_date, dim_location, dim_team).

Facts refer to dimensions by surrogate keys (`date_key`, `location_key`, `team_key`)
instead of names, so Power BI can relate them with simple one-to-many relationships.
"""

from datetime import date, timedelta

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# Covers every fact: weather and prices start in Q3 2006, weather ends on 2026-06-30.
FIRST_DATE = date(2006, 7, 1)
LAST_DATE = date(2026, 6, 30)

# Open end of the current SCD2 row ("valid until further notice").
OPEN_END = date(9999, 12, 31)
OPEN_START = date(1900, 1, 1)


def date_key(column: str) -> F.Column:
    """Integer key of a date in the form yyyymmdd, e.g. 2025-01-02 -> 20250102."""
    return F.date_format(F.col(column), "yyyyMMdd").cast("int")


def dim_date(spark: SparkSession, first: date = FIRST_DATE, last: date = LAST_DATE) -> DataFrame:
    """One row per day with calendar attributes and the football season (July to June)."""
    days = spark.range(1).select(
        F.explode(F.sequence(F.lit(first), F.lit(last))).alias("date")
    )
    year, month = F.year("date"), F.month("date")
    season_start = F.when(month >= 7, year).otherwise(year - 1)
    return days.select(
        date_key("date").alias("date_key"),
        "date",
        year.alias("year"),
        F.quarter("date").alias("quarter"),
        month.alias("month"),
        F.dayofmonth("date").alias("day"),
        # 1 = Monday ... 7 = Sunday.
        ((F.dayofweek("date") + 5) % 7 + 1).alias("day_of_week"),
        F.dayofweek("date").isin(1, 7).alias("is_weekend"),
        F.concat(season_start.cast("string"), F.lit("/"), (season_start + 1).cast("string")).alias(
            "football_season"
        ),
    )


def dim_location(
    spark: SparkSession,
    ranked: dict[str, tuple[float, float]],
    stadium_towns: dict[str, tuple[float, float]],
    voivodeships: dict[str, str],
) -> DataFrame:
    """One row per town (SCD1: names and voivodeships did not change in the covered years)."""
    towns = {**ranked, **stadium_towns}
    rows = [
        (key, town, voivodeships[town], lat, lon, town in ranked)
        for key, (town, (lat, lon)) in enumerate(sorted(towns.items()), start=1)
    ]
    return spark.createDataFrame(
        rows,
        "location_key int, city string, voivodeship string, latitude double, longitude double,"
        " is_ranked boolean",
    )


def team_periods(
    team_towns: dict[str, str], relocations: list[tuple[str, date, date, str]]
) -> list[tuple[str, str, date, date]]:
    """Split each team's history into periods with one home town: (team, town, from, to)."""
    periods = []
    for team, own_town in sorted(team_towns.items()):
        start = OPEN_START
        for _, move_from, move_to, town in sorted(r for r in relocations if r[0] == team):
            if move_from > start:
                periods.append((team, own_town, start, move_from - timedelta(days=1)))
            periods.append((team, town, move_from, move_to))
            start = move_to + timedelta(days=1)
        periods.append((team, own_town, start, OPEN_END))
    return periods


def dim_team(
    spark: SparkSession,
    team_towns: dict[str, str],
    relocations: list[tuple[str, date, date, str]],
) -> DataFrame:
    """SCD2: a new row every time a team's home town changes, with its validity period."""
    rows = [
        (key, team, town, valid_from, valid_to, valid_to == OPEN_END)
        for key, (team, town, valid_from, valid_to) in enumerate(
            team_periods(team_towns, relocations), start=1
        )
    ]
    return spark.createDataFrame(
        rows,
        "team_key int, team string, home_town string, valid_from date, valid_to date,"
        " is_current boolean",
    )
