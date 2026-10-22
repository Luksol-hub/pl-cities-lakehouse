"""Spark session helper for local development and tests."""

from pyspark.sql import SparkSession


def get_spark(app_name: str = "pl-cities-lakehouse") -> SparkSession:
    """Return a local Spark session. On Databricks the existing session is reused."""
    return SparkSession.builder.appName(app_name).master("local[*]").getOrCreate()
