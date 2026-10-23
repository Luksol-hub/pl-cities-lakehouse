"""Gold: fact tables of the star schema, with surrogate keys to the dimensions.

Yearly and quarterly facts point to the first day of their period in dim_date
(e.g. Q3 2025 -> 20250701), so every fact can use one relationship to the calendar.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from pl_cities_lakehouse.common.quality import DataQualityError
from pl_cities_lakehouse.transformations.gold_dimensions import date_key


def with_location_key(df: DataFrame, locations: DataFrame, city_column: str) -> DataFrame:
    """Replace a town name with its location_key; stop if a town is not in dim_location."""
    keyed = df.join(
        locations.select(F.col("city").alias(city_column), "location_key"),
        on=city_column,
        how="left",
    )
    unknown = keyed.filter(F.col("location_key").isNull()).select(city_column).distinct()
    missing = [row[0] for row in unknown.collect()]
    if missing:
        raise DataQualityError(f"Towns missing from dim_location: {sorted(missing)}")
    return keyed.drop(city_column)


def period_start_key(year: str, quarter: str | None = None) -> F.Column:
    """date_key of the first day of a year or of a quarter."""
    month = F.lit(1) if quarter is None else (F.col(quarter) - 1) * 3 + 1
    return F.date_format(F.make_date(F.col(year), month, F.lit(1)), "yyyyMMdd").cast("int")


def fact_weather_daily(weather: DataFrame, locations: DataFrame) -> DataFrame:
    """One row per town and day."""
    return with_location_key(weather, locations, "city").select(
        "location_key",
        date_key("date").alias("date_key"),
        "temp_mean_c",
        "precipitation_mm",
        "wind_max_kmh",
    )


def fact_housing_price(housing: DataFrame, locations: DataFrame) -> DataFrame:
    """One row per market, price type, city and quarter."""
    return with_location_key(housing, locations, "city").select(
        "location_key",
        period_start_key("year", "quarter").alias("date_key"),
        "market",
        "price_type",
        "price_pln_m2",
    )


def fact_wage(wages: DataFrame, locations: DataFrame) -> DataFrame:
    """One row per city and year."""
    return with_location_key(wages, locations, "city").select(
        "location_key", period_start_key("year").alias("date_key"), "wage_pln"
    )


def fact_air_quality(pm10: DataFrame, locations: DataFrame) -> DataFrame:
    """One row per city and year: median smog days over the city's stations."""
    return with_location_key(pm10, locations, "city").select(
        "location_key", period_start_key("year").alias("date_key"), "days_pm10_over_50", "stations"
    )


def team_key_on_match_day(matches: DataFrame, teams: DataFrame, team_column: str) -> DataFrame:
    """SCD2 lookup: the team_key of the dim_team row valid on the match date."""
    version = teams.select(
        F.col("team").alias("_team"),
        F.col("team_key").alias(f"{team_column}_key"),
        "valid_from",
        "valid_to",
    )
    on_match_day = (F.col(team_column) == F.col("_team")) & F.col("match_date").between(
        F.col("valid_from"), F.col("valid_to")
    )
    return matches.join(version, on_match_day, how="left").drop("_team", "valid_from", "valid_to")


def fact_match(matches: DataFrame, locations: DataFrame, teams: DataFrame) -> DataFrame:
    """One row per match, with both teams as they were on match day and match-day weather."""
    keyed = team_key_on_match_day(matches, teams, "home_team")
    keyed = team_key_on_match_day(keyed, teams, "away_team")
    missing = keyed.filter(F.col("home_team_key").isNull() | F.col("away_team_key").isNull())
    if missing.count():
        raise DataQualityError("fact_match: matches without a valid dim_team row")
    return with_location_key(keyed, locations, "town").select(
        date_key("match_date").alias("date_key"),
        "location_key",
        "home_team_key",
        "away_team_key",
        "season",
        "kickoff_time",
        "home_goals",
        "away_goals",
        "result",
        "temp_mean_c",
        "precipitation_mm",
        "wind_max_kmh",
    )


def mart_with_keys(mart: DataFrame, locations: DataFrame) -> DataFrame:
    """Add location_key and date_key to a city-year mart, keeping the readable columns."""
    keyed = with_location_key(mart.withColumn("_city", F.col("city")), locations, "_city")
    return keyed.withColumn("date_key", period_start_key("year"))
