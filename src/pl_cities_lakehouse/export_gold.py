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

from pl_cities_lakehouse.common.cities import CITIES
from pl_cities_lakehouse.common.spark import get_spark
from pl_cities_lakehouse.common.teams import STADIUM_TOWNS, TEAM_TOWNS
from pl_cities_lakehouse.ingestion import football, gios, gus_bdl, nbp_housing, open_meteo
from pl_cities_lakehouse.pipeline import gold_tables, silver_tables


def build_bronze(spark: SparkSession, raw_dir: Path) -> dict[str, DataFrame]:
    """Raw files -> bronze DataFrames, named like the bronze tables on Databricks."""
    cities = list(CITIES)
    nbp_file = raw_dir / "nbp" / "ceny_mieszkan.xlsx"
    football_file = raw_dir / "football" / "POL.csv"
    wages_file = raw_dir / "gus_bdl" / "wages_64428.json"
    return {
        "housing_prices": nbp_housing.to_dataframe(
            spark, nbp_housing.read_records(nbp_file), nbp_file.name
        ),
        "weather_daily": open_meteo.to_dataframe(
            spark, open_meteo.read_records({**CITIES, **STADIUM_TOWNS}, raw_dir / "open_meteo")
        ),
        "wages": gus_bdl.to_dataframe(
            spark, gus_bdl.to_records(gus_bdl.load_raw(wages_file), cities)
        ),
        "pm10": gios.to_dataframe(spark, gios.read_records(raw_dir / "gios", cities)),
        "matches": football.to_dataframe(
            spark, football.read_records(football_file, TEAM_TOWNS), football_file.name
        ),
    }


def build_gold(spark: SparkSession, raw_dir: Path) -> dict[str, DataFrame]:
    """Raw files -> bronze -> silver -> gold, all in memory; returns gold tables by name."""
    silver = silver_tables(build_bronze(spark, raw_dir))
    # Cached: each silver table is used by several gold tables.
    return gold_tables(spark, {name: df.cache() for name, df in silver.items()})


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
