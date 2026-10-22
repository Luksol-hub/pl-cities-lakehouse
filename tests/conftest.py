import pytest

from pl_cities_lakehouse.common.spark import get_spark


@pytest.fixture(scope="session")
def spark():
    """One small Spark session for the whole test run; few threads keep Windows fast."""
    session = get_spark("tests", master="local[2]")
    session.conf.set("spark.sql.shuffle.partitions", "2")
    yield session
    session.stop()
