"""Ekstraklasa match results from football-data.co.uk (one CSV with all seasons since 2012/13).

Bronze keeps every match as published, including the season in progress.
Limiting the seasons to the weather period happens later.
"""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, IntegerType, StringType, StructField, StructType

CSV_URL = "https://www.football-data.co.uk/new/POL.csv"

SCHEMA = StructType(
    [
        StructField("season", StringType(), False),
        StructField("match_date", DateType(), False),
        StructField("kickoff_time", StringType(), True),
        StructField("home_team", StringType(), False),
        StructField("away_team", StringType(), False),
        StructField("town", StringType(), False),
        StructField("home_goals", IntegerType(), False),
        StructField("away_goals", IntegerType(), False),
        StructField("result", StringType(), False),
    ]
)


def download(dest: Path, url: str = CSV_URL) -> Path:
    """Download the CSV to `dest` and return the path."""
    response = requests.get(url, timeout=60, headers={"User-Agent": "pl-cities-lakehouse"})
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return dest


def parse_matches(text: str, team_towns: dict[str, str]) -> list[dict]:
    """Turn the CSV text into one record per match, with the town of the home team's stadium."""
    rows = list(csv.DictReader(io.StringIO(text)))

    teams = {row["Home"] for row in rows} | {row["Away"] for row in rows}
    unknown = sorted(teams - team_towns.keys())
    if unknown:
        raise ValueError(f"Teams without a stadium town: {unknown}")

    records = []
    for row in rows:
        records.append(
            {
                "season": row["Season"],
                # Dates are day/month/year, e.g. "17/08/2012".
                "match_date": datetime.strptime(row["Date"], "%d/%m/%Y").date(),
                "kickoff_time": row["Time"] or None,
                "home_team": row["Home"],
                "away_team": row["Away"],
                "town": team_towns[row["Home"]],
                "home_goals": int(row["HG"]),
                "away_goals": int(row["AG"]),
                # H = home win, D = draw, A = away win.
                "result": row["Res"],
            }
        )
    return records


def read_records(path: Path, team_towns: dict[str, str]) -> list[dict]:
    """Read the saved CSV file into match records."""
    # "utf-8-sig" drops the invisible byte-order mark some tools put at the start of a CSV.
    return parse_matches(path.read_text(encoding="utf-8-sig"), team_towns)


def to_dataframe(spark: SparkSession, records: list[dict], source_file: str) -> DataFrame:
    """Build the bronze DataFrame with load metadata."""
    return (
        spark.createDataFrame(records, schema=SCHEMA)
        .withColumn("source_file", F.lit(source_file))
        .withColumn("ingested_at", F.lit(datetime.now(timezone.utc)))
    )
