"""Silver and gold steps of the pipeline, shared by the local export and the Databricks notebooks.

Both functions take and return DataFrames by table name, so the caller decides where the input
comes from (raw files in memory, or Delta tables) and where the output goes.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from pl_cities_lakehouse.common.cities import CITIES, VOIVODESHIPS
from pl_cities_lakehouse.common.teams import STADIUM_TOWNS, TEAM_RELOCATIONS, TEAM_TOWNS
from pl_cities_lakehouse.transformations.gold_affordability import gold_affordability
from pl_cities_lakehouse.transformations.gold_city_score import gold_city_score
from pl_cities_lakehouse.transformations.gold_dimensions import (
    LAST_DATE,
    dim_date,
    dim_location,
    dim_market_option,
    dim_team,
)
from pl_cities_lakehouse.transformations.gold_facts import (
    fact_air_quality,
    fact_housing_price,
    fact_match,
    fact_wage,
    fact_weather_daily,
    mart_with_keys,
)
from pl_cities_lakehouse.transformations.gold_match_weather import gold_match_weather
from pl_cities_lakehouse.transformations.gold_quality_of_life import gold_quality_of_life
from pl_cities_lakehouse.transformations.gold_weather import gold_weather_year
from pl_cities_lakehouse.transformations.silver_air_quality import silver_pm10
from pl_cities_lakehouse.transformations.silver_housing import silver_housing
from pl_cities_lakehouse.transformations.silver_matches import silver_matches
from pl_cities_lakehouse.transformations.silver_wages import silver_wages
from pl_cities_lakehouse.transformations.silver_weather import silver_weather


def silver_tables(bronze: dict[str, DataFrame]) -> dict[str, DataFrame]:
    """Bronze -> silver: quality checks and business rules; keys are the table names."""
    weather = silver_weather(bronze["weather_daily"])
    return {
        "weather_daily": weather,
        "housing_prices": silver_housing(bronze["housing_prices"]),
        "wages": silver_wages(bronze["wages"]),
        "pm10": silver_pm10(bronze["pm10"]),
        "matches": silver_matches(bronze["matches"], weather),
    }


def gold_tables(spark: SparkSession, silver: dict[str, DataFrame]) -> dict[str, DataFrame]:
    """Silver -> gold: star schema dimensions, facts and the two marts."""
    weather = silver["weather_daily"]
    locations = dim_location(spark, CITIES, STADIUM_TOWNS, VOIVODESHIPS)
    teams = dim_team(spark, TEAM_TOWNS, TEAM_RELOCATIONS)

    # The calendar must cover every loaded day; weather grows with each incremental load.
    last_weather_day = weather.agg(F.max("date")).first()[0]
    calendar_end = max(LAST_DATE, last_weather_day) if last_weather_day else LAST_DATE

    quality_of_life = gold_quality_of_life(gold_weather_year(weather, list(CITIES)), silver["pm10"])
    affordability = gold_affordability(silver["housing_prices"], silver["wages"])
    city_score = gold_city_score(quality_of_life, affordability)

    return {
        "dim_date": dim_date(spark, last=calendar_end),
        "dim_location": locations,
        "dim_team": teams,
        "dim_market_option": dim_market_option(spark),
        "fact_weather_daily": fact_weather_daily(weather, locations),
        "fact_housing_price": fact_housing_price(silver["housing_prices"], locations),
        "fact_wage": fact_wage(silver["wages"], locations),
        "fact_air_quality": fact_air_quality(silver["pm10"], locations),
        "fact_match": fact_match(silver["matches"], locations, teams),
        "mart_city_score": mart_with_keys(city_score, locations),
        "mart_match_weather": gold_match_weather(silver["matches"]),
    }
