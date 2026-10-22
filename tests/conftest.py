import pytest

from pl_cities_lakehouse.common.spark import get_spark


@pytest.fixture(scope="session")
def spark():
    """One small Spark session for the whole test run.

    Test tables have a handful of rows, so one thread and one partition avoid the cost of
    splitting work that is not worth splitting (each extra task costs time on Windows).
    """
    session = get_spark("tests", master="local[1]")
    session.conf.set("spark.sql.shuffle.partitions", "1")
    yield session
    session.stop()
