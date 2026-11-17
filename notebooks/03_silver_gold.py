# Databricks notebook source
# MAGIC %md
# MAGIC # Silver and gold
# MAGIC
# MAGIC Reads the bronze tables, applies the same functions as the local pipeline
# MAGIC (`pl_cities_lakehouse.pipeline`) and saves every result as a Delta table:
# MAGIC
# MAGIC - **silver** (`pl_cities.silver.*`): quality checks and business rules; a broken rule stops
# MAGIC   the run with `DataQualityError` before anything bad reaches gold (fail fast).
# MAGIC - **gold** (`pl_cities.gold.*`): star schema (dimensions, facts) and the two marts
# MAGIC   for Power BI.
# MAGIC
# MAGIC Silver and gold are recalculated from scratch every run (full overwrite): the data is small
# MAGIC and indices like min-max normalisation depend on all cities of a year at once.

# COMMAND ----------

import sys
from pathlib import Path

# In a Databricks Git folder the working directory is the notebook's folder,
# so the package sources are one level up, in `src`.
REPO_ROOT = Path.cwd().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pl_cities_lakehouse.pipeline import gold_tables, silver_tables

BRONZE = ["weather_daily", "housing_prices", "wages", "pm10", "matches"]


def save(df, table: str) -> None:
    """Full overwrite of a table; prints the row count as a quick check."""
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    print(f"{table:40} {spark.table(table).count():>8} rows")

# COMMAND ----------

# Bronze -> silver. Gold then reads the saved silver tables, so lineage in Unity Catalog
# shows the whole chain bronze -> silver -> gold.
bronze = {name: spark.table(f"pl_cities.bronze.{name}") for name in BRONZE}
for name, df in silver_tables(bronze).items():
    save(df, f"pl_cities.silver.{name}")

# COMMAND ----------

# Silver -> gold.
silver = {name: spark.table(f"pl_cities.silver.{name}") for name in BRONZE}
for name, df in gold_tables(spark, silver).items():
    save(df, f"pl_cities.gold.{name}")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Same check as in Power BI (docs/progress.md): top 3 of 2025 per market.
# MAGIC -- Expected: secondary - Szczecin 0.64, primary - Zielona Góra 0.80.
# MAGIC SELECT market, final_rank, city, ROUND(final_score, 2) AS final_score
# MAGIC FROM pl_cities.gold.mart_city_score
# MAGIC WHERE year = 2025 AND final_rank <= 3
# MAGIC ORDER BY market, final_rank
