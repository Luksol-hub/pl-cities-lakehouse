# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: weather (Open-Meteo)
# MAGIC
# MAGIC 1. Download the API response for each town as a JSON file into the Unity Catalog volume.
# MAGIC 2. Turn the files into daily records and save them as the Delta table
# MAGIC    `pl_cities.bronze.weather_daily`.
# MAGIC
# MAGIC The logic lives in `src/pl_cities_lakehouse`; this notebook only runs it.

# COMMAND ----------

import sys
from pathlib import Path

# In a Databricks Git folder the working directory is the notebook's folder,
# so the package sources are one level up, in `src`.
REPO_ROOT = Path.cwd().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pl_cities_lakehouse.common.cities import CITIES
from pl_cities_lakehouse.common.teams import STADIUM_TOWNS
from pl_cities_lakehouse.ingestion import open_meteo

RAW_DIR = Path("/Volumes/pl_cities/raw/files/open_meteo")
TABLE = "pl_cities.bronze.weather_daily"

# Same towns as locally: 17 cities plus the stadium towns needed by module B.
towns = {**CITIES, **STADIUM_TOWNS}
print(len(towns), "towns")

# COMMAND ----------

# Download: one JSON file per town. Files that already exist are skipped,
# so a rerun only fetches what is missing (and does not hit the API rate limit again).
paths = open_meteo.save_raw_responses(towns, RAW_DIR)
print(len(paths), "files in", RAW_DIR)

# COMMAND ----------

# Files -> DataFrame with load metadata (source, ingested_at) -> Delta table.
# Full overwrite for now; incremental loading with MERGE comes in the next step.
records = open_meteo.read_records(towns, RAW_DIR)
bronze = open_meteo.to_dataframe(spark, records)

bronze.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(TABLE)
print(spark.table(TABLE).count(), "rows in", TABLE)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT city, MIN(date) AS first_day, MAX(date) AS last_day, COUNT(*) AS days
# MAGIC FROM pl_cities.bronze.weather_daily
# MAGIC GROUP BY city
# MAGIC ORDER BY city
