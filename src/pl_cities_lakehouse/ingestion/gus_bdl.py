"""GUS BDL (Bank Danych Lokalnych): download yearly wages for cities with powiat rights."""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

API_URL = "https://bdl.stat.gov.pl/api/v1"

# Average monthly gross wage in PLN, published for powiats (cities with powiat rights included).
WAGE_VARIABLE_ID = 64428
POWIAT_LEVEL = 5

SOURCE = f"gus-bdl-{WAGE_VARIABLE_ID}"

SCHEMA = StructType(
    [
        StructField("city", StringType(), False),
        StructField("year", IntegerType(), False),
        StructField("wage_pln", DoubleType(), False),
    ]
)


def fetch_variable(variable_id: int, unit_level: int = POWIAT_LEVEL) -> list[dict]:
    """Return values of one variable for all units of a level, following every page."""
    url = f"{API_URL}/data/by-variable/{variable_id}"
    params = {"unit-level": unit_level, "page-size": 100, "format": "json", "lang": "pl"}
    results = []
    while url:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        page = response.json()
        results.extend(page["results"])
        # The link to the next page already holds all parameters; the last page has none.
        url = page.get("links", {}).get("next")
        params = None
    return results


def gus_unit_name(city: str) -> str:
    """GUS name of a city with powiat rights: 'Kraków' -> 'Powiat m. Kraków'."""
    # Warsaw is the capital city ("miasto stołeczne"), so GUS adds "st.".
    if city == "Warszawa":
        return "Powiat m. st. Warszawa"
    return f"Powiat m. {city}"


def to_records(results: list[dict], cities: list[str]) -> list[dict]:
    """Pick our cities out of all powiats and return one record per city and year."""
    by_name = {unit["name"]: unit for unit in results}
    missing = [city for city in cities if gus_unit_name(city) not in by_name]
    if missing:
        raise ValueError(f"Cities not found in GUS data: {missing}")

    records = []
    for city in cities:
        for value in by_name[gus_unit_name(city)]["values"]:
            # attrId 1 marks a regular value; other codes mean missing or confidential data.
            if value["attrId"] == 1:
                records.append(
                    {"city": city, "year": int(value["year"]), "wage_pln": float(value["val"])}
                )
    return records


def save_raw(results: list[dict], path: Path) -> Path:
    """Save the downloaded units as-is to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    return path


def load_raw(path: Path) -> list[dict]:
    """Read units saved by `save_raw`."""
    return json.loads(path.read_text(encoding="utf-8"))


def to_dataframe(spark: SparkSession, records: list[dict]) -> DataFrame:
    """Build the bronze DataFrame with load metadata."""
    return (
        spark.createDataFrame(records, schema=SCHEMA)
        .withColumn("source", F.lit(SOURCE))
        .withColumn("ingested_at", F.lit(datetime.now(timezone.utc)))
    )
