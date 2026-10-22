"""Data quality checks for silver tables.

Each check counts the rows that break a rule. `assert_quality` runs a set of checks
and stops the pipeline with a list of every problem found, so bad data never reaches gold.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


class DataQualityError(Exception):
    """Raised when a table breaks one or more quality rules."""


def duplicate_keys(df: DataFrame, keys: list[str]) -> int:
    """Number of key values that appear in more than one row."""
    return df.groupBy(*keys).count().filter(F.col("count") > 1).count()


def null_values(df: DataFrame, column: str) -> int:
    """Number of rows with an empty value in `column`."""
    return df.filter(F.col(column).isNull()).count()


def out_of_range(df: DataFrame, column: str, low: float, high: float) -> int:
    """Number of rows where `column` is outside [low, high]. Empty values are not counted."""
    return df.filter((F.col(column) < low) | (F.col(column) > high)).count()


def missing_days(df: DataFrame, group: str, date_column: str) -> dict[str, int]:
    """Days missing between the first and last date of each group, for groups with gaps."""
    spans = df.groupBy(group).agg(
        F.count(date_column).alias("days"),
        (F.datediff(F.max(date_column), F.min(date_column)) + 1).alias("expected"),
    )
    gaps = spans.filter(F.col("days") < F.col("expected")).collect()
    return {row[group]: row["expected"] - row["days"] for row in gaps}


def assert_quality(
    df: DataFrame,
    table: str,
    keys: list[str],
    not_null: list[str] = (),
    ranges: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Run the checks and raise DataQualityError listing every rule that failed."""
    problems = []

    duplicates = duplicate_keys(df, keys)
    if duplicates:
        problems.append(f"{duplicates} duplicated keys {keys}")

    # Every Spark action reads the whole table again, so count all empty and out-of-range
    # values in a single pass instead of one pass per rule.
    ranges = ranges or {}
    counts = {}
    for column in not_null:
        counts[f"{column} empty"] = F.count_if(F.col(column).isNull())
    for column, (low, high) in ranges.items():
        outside = (F.col(column) < low) | (F.col(column) > high)
        counts[f"{column} outside"] = F.count_if(outside)

    if counts:
        totals = df.agg(*[rule.alias(name) for name, rule in counts.items()]).first()
        for column in not_null:
            if totals[f"{column} empty"]:
                problems.append(f"{totals[f'{column} empty']} empty values in {column}")
        for column, (low, high) in ranges.items():
            if totals[f"{column} outside"]:
                count = totals[f"{column} outside"]
                problems.append(f"{count} values of {column} outside [{low}, {high}]")

    if problems:
        raise DataQualityError(f"{table}: " + "; ".join(problems))
