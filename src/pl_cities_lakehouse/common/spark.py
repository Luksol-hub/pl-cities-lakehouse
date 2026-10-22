"""Spark session helper for local development and tests."""

import os
import sys

from pyspark.sql import SparkSession


def get_spark(app_name: str = "pl-cities-lakehouse") -> SparkSession:
    """Return a local Spark session. On Databricks the existing session is reused."""
    # Spark workers start `python` from PATH by default; on Windows that is often missing
    # or a Microsoft Store alias, so point them at the interpreter running this code.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    return SparkSession.builder.appName(app_name).master("local[*]").getOrCreate()
