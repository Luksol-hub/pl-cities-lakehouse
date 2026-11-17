from pl_cities_lakehouse.common.delta import merge_sql


def test_merge_sql_matches_on_all_keys():
    sql = merge_sql("pl_cities.bronze.weather_daily", "updates", ["city", "date"])

    assert sql == (
        "MERGE INTO pl_cities.bronze.weather_daily AS t USING updates AS s "
        "ON t.city = s.city AND t.date = s.date "
        "WHEN MATCHED THEN UPDATE SET * "
        "WHEN NOT MATCHED THEN INSERT *"
    )
