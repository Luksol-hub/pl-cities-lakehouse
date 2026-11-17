"""Delta Lake helpers that run on Databricks (local Spark on Windows cannot write Delta)."""

from pyspark.sql import DataFrame


def merge_sql(target: str, source_view: str, keys: list[str]) -> str:
    """MERGE statement: update rows whose keys already exist in the target, insert the rest."""
    condition = " AND ".join(f"t.{key} = s.{key}" for key in keys)
    return (
        f"MERGE INTO {target} AS t USING {source_view} AS s ON {condition} "
        "WHEN MATCHED THEN UPDATE SET * "
        "WHEN NOT MATCHED THEN INSERT *"
    )


def merge_into(updates: DataFrame, target: str, keys: list[str]) -> None:
    """Upsert `updates` into the Delta table `target`, matching rows on `keys`.

    Running it twice with the same data gives the same table (idempotent), because
    existing keys are updated instead of inserted again.
    """
    view = "merge_source"
    updates.createOrReplaceTempView(view)
    updates.sparkSession.sql(merge_sql(target, view, keys))
