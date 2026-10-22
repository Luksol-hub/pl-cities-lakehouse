import pl_cities_lakehouse


def test_version():
    assert pl_cities_lakehouse.__version__ == "0.1.0"


def test_spark_runs_locally(spark):
    df = spark.createDataFrame([(1, "Krakow"), (2, "Wroclaw")], ["id", "city"])
    assert df.count() == 2
