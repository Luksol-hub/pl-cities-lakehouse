"""Build the whole pipeline from raw files and save every gold table as a Parquet file.

Local stand-in for writing Delta tables, which Spark cannot do on Windows without winutils:
gold tables are small, so they are moved to pandas (`toPandas`) and written with pyarrow.
Power BI Desktop reads the folder; on Databricks the same tables become Delta tables.

Run locally (after the raw files are downloaded):
    python -m pl_cities_lakehouse.export_gold
"""

import argparse
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from pl_cities_lakehouse.common.cities import CITIES, VOIVODESHIPS
from pl_cities_lakehouse.common.spark import get_spark
from pl_cities_lakehouse.common.teams import STADIUM_TOWNS, TEAM_RELOCATIONS, TEAM_TOWNS
from pl_cities_lakehouse.ingestion import football, gios, gus_bdl, nbp_housing, open_meteo
from pl_cities_lakehouse.transformations.gold_affordability import gold_affordability
from pl_cities_lakehouse.transformations.gold_city_score import gold_city_score
from pl_cities_lakehouse.transformations.gold_dimensions import dim_date, dim_location, dim_team
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


def build_gold(spark: SparkSession, raw_dir: Path) -> dict[str, DataFrame]:
    """Raw files -> bronze -> silver -> gold, all in memory; returns gold tables by name."""
    cities = list(CITIES)
    all_towns = {**CITIES, **STADIUM_TOWNS}

    # Bronze
    nbp_file = raw_dir / "nbp" / "ceny_mieszkan.xlsx"
    football_file = raw_dir / "football" / "POL.csv"
    wages_file = raw_dir / "gus_bdl" / "wages_64428.json"
    bronze_housing = nbp_housing.to_dataframe(
        spark, nbp_housing.read_records(nbp_file), nbp_file.name
    )
    bronze_weather = open_meteo.to_dataframe(
        spark, open_meteo.read_records(all_towns, raw_dir / "open_meteo")
    )
    bronze_wages = gus_bdl.to_dataframe(
        spark, gus_bdl.to_records(gus_bdl.load_raw(wages_file), cities)
    )
    bronze_pm10 = gios.to_dataframe(spark, gios.read_records(raw_dir / "gios", cities))
    bronze_matches = football.to_dataframe(
        spark, football.read_records(football_file, TEAM_TOWNS), football_file.name
    )

    # Silver (cached: each is used by several gold tables)
    weather = silver_weather(bronze_weather).cache()
    housing = silver_housing(bronze_housing).cache()
    wages = silver_wages(bronze_wages).cache()
    pm10 = silver_pm10(bronze_pm10).cache()
    matches = silver_matches(bronze_matches, weather).cache()

    # Gold: dimensions
    locations = dim_location(spark, CITIES, STADIUM_TOWNS, VOIVODESHIPS).cache()
    teams = dim_team(spark, TEAM_TOWNS, TEAM_RELOCATIONS).cache()

    # Gold: marts
    quality_of_life = gold_quality_of_life(gold_weather_year(weather, cities), pm10)
    affordability = gold_affordability(housing, wages)
    city_score = gold_city_score(quality_of_life, affordability)

    return {
        "dim_date": dim_date(spark),
        "dim_location": locations,
        "dim_team": teams,
        "fact_weather_daily": fact_weather_daily(weather, locations),
        "fact_housing_price": fact_housing_price(housing, locations),
        "fact_wage": fact_wage(wages, locations),
        "fact_air_quality": fact_air_quality(pm10, locations),
        "fact_match": fact_match(matches, locations, teams),
        "mart_city_score": mart_with_keys(city_score, locations),
        "mart_match_weather": gold_match_weather(matches),
    }


def export(tables: dict[str, DataFrame], out_dir: Path) -> dict[str, int]:
    """Write each table to `<out_dir>/<name>.parquet`; returns row counts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, df in tables.items():
        frame = df.toPandas()
        frame.to_parquet(out_dir / f"{name}.parquet", index=False)
        counts[name] = len(frame)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/gold"))
    args = parser.parse_args()

    spark = get_spark("export-gold")
    spark.sparkContext.setLogLevel("ERROR")
    for name, rows in export(build_gold(spark, args.raw), args.out).items():
        print(f"{name:20} {rows:>8} rows")


if __name__ == "__main__":
    main()
