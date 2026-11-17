# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: snapshot sources (NBP, GUS BDL, GIOŚ, football)
# MAGIC
# MAGIC Unlike weather, these sources publish their **whole history in every file**, so each run
# MAGIC downloads a fresh copy and **overwrites** the bronze table (full load).
# MAGIC Raw files go to the volume `pl_cities.raw.files`, in a folder named after the load date,
# MAGIC so older copies stay available (raw is never overwritten).
# MAGIC
# MAGIC | Source | Raw file | Bronze table |
# MAGIC | --- | --- | --- |
# MAGIC | NBP housing prices | `nbp/<date>/ceny_mieszkan.xlsx` | `pl_cities.bronze.housing_prices` |
# MAGIC | GUS BDL wages | `gus_bdl/<date>/wages_64428.json` | `pl_cities.bronze.wages` |
# MAGIC | GIOŚ PM10 | `gios/*.xlsx` (yearly archive, downloaded once) | `pl_cities.bronze.pm10` |
# MAGIC | Ekstraklasa matches | `football/<date>/POL.csv` | `pl_cities.bronze.matches` |

# COMMAND ----------

# MAGIC %pip install openpyxl --quiet

# COMMAND ----------

import sys
from datetime import date
from pathlib import Path

# In a Databricks Git folder the working directory is the notebook's folder,
# so the package sources are one level up, in `src`.
REPO_ROOT = Path.cwd().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pl_cities_lakehouse.common.cities import CITIES
from pl_cities_lakehouse.common.teams import TEAM_TOWNS
from pl_cities_lakehouse.ingestion import football, gios, gus_bdl, nbp_housing

RAW = Path("/Volumes/pl_cities/raw/files")
TODAY = date.today().isoformat()
cities = list(CITIES)


def save(df, table: str) -> None:
    """Full overwrite of a bronze table; prints the row count as a quick check."""
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    print(f"{table:35} {spark.table(table).count():>8} rows")

# COMMAND ----------

# NBP housing prices (Excel, one sheet per market).
nbp_file = nbp_housing.download(RAW / "nbp" / TODAY / "ceny_mieszkan.xlsx")
save(
    nbp_housing.to_dataframe(spark, nbp_housing.read_records(nbp_file), nbp_file.name),
    "pl_cities.bronze.housing_prices",
)

# COMMAND ----------

# GUS BDL wages (API with pagination); the raw answer is saved before parsing.
wages_file = gus_bdl.save_raw(
    gus_bdl.fetch_variable(gus_bdl.WAGE_VARIABLE_ID),
    RAW / "gus_bdl" / TODAY / f"wages_{gus_bdl.WAGE_VARIABLE_ID}.json",
)
save(
    gus_bdl.to_dataframe(spark, gus_bdl.to_records(gus_bdl.load_raw(wages_file), cities)),
    "pl_cities.bronze.wages",
)

# COMMAND ----------

# GIOŚ PM10 (two Excel files: statistics and station metadata). The archive changes once
# a year, so files already in the volume are not downloaded again.
gios.download(RAW / "gios")
save(gios.to_dataframe(spark, gios.read_records(RAW / "gios", cities)), "pl_cities.bronze.pm10")

# COMMAND ----------

# Ekstraklasa matches (CSV); team names are mapped to stadium towns while parsing.
matches_file = football.download(RAW / "football" / TODAY / "POL.csv")
save(
    football.to_dataframe(
        spark, football.read_records(matches_file, TEAM_TOWNS), matches_file.name
    ),
    "pl_cities.bronze.matches",
)

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW TABLES IN pl_cities.bronze
