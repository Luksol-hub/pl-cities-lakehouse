"""Silver: Ekstraklasa matches with the weather on match day in the town of the match.

Only full seasons covered by the weather data are kept (2012/13 to 2025/26).
The town is the home team's own town, unless the club was playing elsewhere at the time
(`TEAM_RELOCATIONS`). Weather is daily: the rain is the total for the whole day.
"""

from datetime import date

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from pl_cities_lakehouse.common.quality import DataQualityError, assert_quality
from pl_cities_lakehouse.common.teams import TEAM_RELOCATIONS

# Weather is downloaded up to 2026-06-30, so 2025/26 is the last full season.
FIRST_SEASON = "2012/2013"
LAST_SEASON = "2025/2026"

MATCH_COLUMNS = [
    "season",
    "match_date",
    "kickoff_time",
    "home_team",
    "away_team",
    "town",
    "home_goals",
    "away_goals",
    "result",
]
WEATHER_COLUMNS = ["temp_mean_c", "precipitation_mm", "wind_max_kmh"]


def apply_relocations(
    matches: DataFrame, relocations: list[tuple[str, date, date, str]]
) -> DataFrame:
    """Replace the town of matches played while the home team was based in another town."""
    moves = matches.sparkSession.createDataFrame(
        relocations, "team string, valid_from date, valid_to date, moved_town string"
    )
    # A range join: the match date must fall inside the relocation period.
    in_period = (F.col("home_team") == F.col("team")) & F.col("match_date").between(
        F.col("valid_from"), F.col("valid_to")
    )
    return (
        matches.join(moves, in_period, how="left")
        .withColumn("town", F.coalesce("moved_town", "town"))
        .drop("team", "valid_from", "valid_to", "moved_town")
    )


def silver_matches(
    bronze_matches: DataFrame,
    weather: DataFrame,
    relocations: list[tuple[str, date, date, str]] = TEAM_RELOCATIONS,
) -> DataFrame:
    """Return one row per match with match-day weather; stop with DataQualityError on bad data.

    `weather` is the silver weather table (one row per town and day).
    """
    # Season labels like "2012/2013" sort correctly as text.
    in_seasons = bronze_matches.filter(F.col("season").between(FIRST_SEASON, LAST_SEASON))
    matches = apply_relocations(in_seasons, relocations)

    # A team plays at most one home match a day; overlapping relocations would also show here.
    assert_quality(
        matches,
        table="silver_matches",
        keys=["match_date", "home_team"],
        ranges={"home_goals": (0, 20), "away_goals": (0, 20)},
    )

    # The result must agree with the goals: H when home scored more, D when equal, A otherwise.
    expected = (
        F.when(F.col("home_goals") > F.col("away_goals"), "H")
        .when(F.col("home_goals") == F.col("away_goals"), "D")
        .otherwise("A")
    )
    inconsistent = matches.filter(F.col("result") != expected).count()
    if inconsistent:
        raise DataQualityError(f"silver_matches: {inconsistent} results do not match the goals")

    # Left join keeps every match even without weather, so we can count and report the gaps.
    joined = matches.select(*MATCH_COLUMNS).join(
        weather.select(
            F.col("city").alias("town"), F.col("date").alias("match_date"), *WEATHER_COLUMNS
        ),
        on=["town", "match_date"],
        how="left",
    )

    without_weather = joined.filter(F.col("temp_mean_c").isNull()).count()
    if without_weather:
        raise DataQualityError(f"silver_matches: {without_weather} matches without weather")

    return joined.select(*MATCH_COLUMNS, *WEATHER_COLUMNS)
