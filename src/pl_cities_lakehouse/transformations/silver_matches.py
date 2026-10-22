"""Silver: Ekstraklasa matches with the weather on match day in the town of the match.

Only full seasons covered by the weather data are kept (2012/13 to 2025/26).
Weather is daily: the rain is the total for the whole day, not just the 90 minutes.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from pl_cities_lakehouse.common.quality import DataQualityError, assert_quality

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


def silver_matches(bronze_matches: DataFrame, weather: DataFrame) -> DataFrame:
    """Return one row per match with match-day weather; stop with DataQualityError on bad data.

    `weather` is the silver weather table (one row per town and day).
    """
    # Season labels like "2012/2013" sort correctly as text.
    matches = bronze_matches.filter(F.col("season").between(FIRST_SEASON, LAST_SEASON))

    # A team plays at most one home match a day.
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
