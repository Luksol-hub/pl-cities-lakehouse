"""NBP housing prices (BaRN): download the Excel file and load it into the bronze layer.

The workbook has one sheet per market. Each sheet holds side-by-side blocks:
a "Kwartał" column followed by one column per city and a few weighted means.
We keep offer and transaction prices per city and skip means and hedonic indices.

Run locally:
    python -m pl_cities_lakehouse.ingestion.nbp_housing
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import requests
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from pl_cities_lakehouse.common.spark import get_spark

NBP_HOUSING_URL = "https://static.nbp.pl/dane/rynek-nieruchomosci/ceny_mieszkan.xlsx"

SHEETS = {
    "Rynek pierwotny": "primary",
    "Rynek wtórny": "secondary",
}

PRICE_TYPES = {
    "Ceny ofertowe": "offer",
    "Ceny transakcyjne": "transaction",
}

# 16 voivodeship capitals and Gdynia. A different set means the layout changed.
EXPECTED_CITIES = {
    "Białystok", "Bydgoszcz", "Gdańsk", "Gdynia", "Katowice", "Kielce", "Kraków",
    "Lublin", "Łódź", "Olsztyn", "Opole", "Poznań", "Rzeszów", "Szczecin",
    "Warszawa", "Wrocław", "Zielona Góra",
}

ROMAN_QUARTERS = {"I": 1, "II": 2, "III": 3, "IV": 4}
QUARTER_LABEL = re.compile(r"^(I|II|III|IV) \d{4}$")

SCHEMA = StructType(
    [
        StructField("market", StringType(), False),
        StructField("price_type", StringType(), False),
        StructField("city", StringType(), False),
        StructField("year", IntegerType(), False),
        StructField("quarter", IntegerType(), False),
        StructField("price_pln_m2", DoubleType(), False),
    ]
)


def download(dest: Path, url: str = NBP_HOUSING_URL) -> Path:
    """Download the NBP workbook to `dest` and return the path."""
    response = requests.get(url, timeout=60, headers={"User-Agent": "pl-cities-lakehouse"})
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return dest


def parse_quarter(label: str) -> tuple[int, int]:
    """Turn a label like 'III 2006' into (2006, 3)."""
    roman, year = label.split()
    return int(year), ROMAN_QUARTERS[roman]


def parse_sheet(rows: list[tuple], market: str) -> list[dict]:
    """Turn the rows of one market sheet into long records, one per city and quarter."""
    header_idx = next(i for i, row in enumerate(rows) if row and row[0] == "Kwartał")
    header = rows[header_idx]

    # Block titles ("Ceny ofertowe", ...) sit a few rows above the header, above either
    # the "Kwartał" column or the first city column (NBP is not consistent here).
    titles = {}
    for row in rows[:header_idx]:
        for col, value in enumerate(row):
            if isinstance(value, str) and value.strip() in PRICE_TYPES:
                titles[col] = PRICE_TYPES[value.strip()]

    records = []
    for start, value in enumerate(header):
        price_type = titles.get(start + 1) or titles.get(start)
        if value != "Kwartał" or price_type is None:
            continue

        city_cols = {}
        for col in range(start + 1, len(header)):
            name = header[col]
            if not isinstance(name, str) or "miast" in name or name == "Kwartał":
                break
            city_cols[col] = name.strip().rstrip("*")

        found = set(city_cols.values())
        if found != EXPECTED_CITIES:
            missing, extra = sorted(EXPECTED_CITIES - found), sorted(found - EXPECTED_CITIES)
            raise ValueError(
                f"{market}/{price_type}: unexpected cities. Missing: {missing}, extra: {extra}"
            )

        for row in rows[header_idx + 1 :]:
            label = row[start] if start < len(row) else None
            # Footnotes and empty rows have no quarter label.
            if not isinstance(label, str) or not QUARTER_LABEL.match(label.strip()):
                continue
            year, quarter = parse_quarter(label.strip())
            for col, city in city_cols.items():
                price = row[col] if col < len(row) else None
                if isinstance(price, (int, float)):
                    records.append(
                        {
                            "market": market,
                            "price_type": price_type,
                            "city": city,
                            "year": year,
                            "quarter": quarter,
                            "price_pln_m2": float(price),
                        }
                    )

    if not records:
        raise ValueError(f"{market}: no price blocks found")
    return records


def read_records(path: Path) -> list[dict]:
    """Read all market sheets of the NBP workbook into long records."""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        records = []
        for sheet, market in SHEETS.items():
            rows = list(workbook[sheet].iter_rows(values_only=True))
            records.extend(parse_sheet(rows, market))
        return records
    finally:
        workbook.close()


def to_dataframe(spark: SparkSession, records: list[dict], source_file: str) -> DataFrame:
    """Build the bronze DataFrame with load metadata."""
    return (
        spark.createDataFrame(records, schema=SCHEMA)
        .withColumn("source_file", F.lit(source_file))
        .withColumn("ingested_at", F.lit(datetime.now(timezone.utc)))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw/nbp/ceny_mieszkan.xlsx"))
    parser.add_argument("--out", type=Path, default=Path("data/bronze/nbp_housing_prices"))
    parser.add_argument("--skip-download", action="store_true", help="use the existing raw file")
    args = parser.parse_args()

    if not args.skip_download:
        download(args.raw)
    records = read_records(args.raw)

    spark = get_spark("nbp-housing")
    df = to_dataframe(spark, records, args.raw.name)
    # Full overwrite: NBP republishes the whole history in every file.
    df.write.mode("overwrite").partitionBy("market").parquet(str(args.out))
    print(f"Wrote {df.count()} rows to {args.out}")


if __name__ == "__main__":
    main()
