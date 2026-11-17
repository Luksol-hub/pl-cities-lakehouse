# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: weather (Open-Meteo)
# MAGIC
# MAGIC 1. **First run** (no table yet): download the whole history, one JSON file per town,
# MAGIC    into the Unity Catalog volume and save it as the Delta table
# MAGIC    `pl_cities.bronze.weather_daily`.
# MAGIC 2. **Every run**: download only the missing days (plus the last week again, because recent
# MAGIC    values can still be corrected) and upsert them with `MERGE` on `city` + `date`.
# MAGIC
# MAGIC The logic lives in `src/pl_cities_lakehouse`; this notebook only runs it.

# COMMAND ----------

import sys
from datetime import date
from pathlib import Path

# In a Databricks Git folder the working directory is the notebook's folder,
# so the package sources are one level up, in `src`.
REPO_ROOT = Path.cwd().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pl_cities_lakehouse.common.cities import CITIES
from pl_cities_lakehouse.common.delta import merge_into
from pl_cities_lakehouse.common.teams import STADIUM_TOWNS
from pl_cities_lakehouse.ingestion import open_meteo

RAW_DIR = Path("/Volumes/pl_cities/raw/files/open_meteo")
TABLE = "pl_cities.bronze.weather_daily"
KEYS = ["city", "date"]

# Same towns as locally: 17 cities plus the stadium towns needed by module B.
towns = {**CITIES, **STADIUM_TOWNS}
print(len(towns), "towns")

# COMMAND ----------

# First run only: the whole history (files that already exist are not downloaded again).
if not spark.catalog.tableExists(TABLE):
    open_meteo.save_raw_responses(towns, RAW_DIR)
    records = open_meteo.read_records(towns, RAW_DIR)
    open_meteo.to_dataframe(spark, records).write.saveAsTable(TABLE)
    print("created", TABLE)
else:
    print(TABLE, "exists, skipping the full load")

# COMMAND ----------

# Every run: what is already loaded -> which days to fetch -> raw files -> MERGE.
loaded = open_meteo.last_dates(spark.table(TABLE))
ranges = open_meteo.incremental_ranges(towns, loaded, date.today())
for city, (start, end) in sorted(ranges.items()):
    print(f"{city:25} {start} -> {end}")

saved = open_meteo.save_increments(towns, ranges, RAW_DIR / "increments")
records = open_meteo.read_increment_records(saved)
if records:
    merge_into(open_meteo.to_dataframe(spark, records), TABLE, KEYS)
print(len(records), "rows merged into", TABLE)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Every write is a new table version: the full load, then one MERGE per run
# MAGIC -- (see `operation` and `operationMetrics`: numTargetRowsInserted / numTargetRowsUpdated).
# MAGIC DESCRIBE HISTORY pl_cities.bronze.weather_daily

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT city, MIN(date) AS first_day, MAX(date) AS last_day, COUNT(*) AS days
# MAGIC FROM pl_cities.bronze.weather_daily
# MAGIC GROUP BY city
# MAGIC ORDER BY city
