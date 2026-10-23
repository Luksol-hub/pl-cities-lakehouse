import pytest

from pl_cities_lakehouse.transformations.gold_affordability import gold_affordability

HOUSING_SCHEMA = (
    "market string, price_type string, city string, year int, quarter int, price_pln_m2 double"
)
WAGES_SCHEMA = "city string, year int, wage_pln double"


def run(spark, housing_rows, wage_rows):
    return gold_affordability(
        spark.createDataFrame(housing_rows, HOUSING_SCHEMA),
        spark.createDataFrame(wage_rows, WAGES_SCHEMA),
    )


def quarters(market, price_type, city, year, prices):
    # float(): Spark rejects an int in a double column, even 14000 for 14000.0.
    return [(market, price_type, city, year, q, float(p)) for q, p in enumerate(prices, start=1)]


def test_m2_per_wage_from_yearly_average_transaction_price(spark):
    housing = quarters("secondary", "transaction", "Kraków", 2025, [14000, 15000, 16000, 15000])
    wages = [("Kraków", 2025, 11250.0)]

    row = run(spark, housing, wages).collect()[0]

    assert row.avg_price_pln_m2 == pytest.approx(15000.0)
    assert row.quarters == 4
    assert row.m2_per_wage == pytest.approx(0.75)  # 11 250 / 15 000


def test_markets_are_kept_separately_and_offer_prices_ignored(spark):
    housing = [
        *quarters("primary", "transaction", "Kraków", 2025, [16000] * 4),
        *quarters("secondary", "transaction", "Kraków", 2025, [15000] * 4),
        *quarters("secondary", "offer", "Kraków", 2025, [99999] * 4),
    ]
    wages = [("Kraków", 2025, 12000.0)]

    rows = {r.market: r.m2_per_wage for r in run(spark, housing, wages).collect()}

    assert rows == pytest.approx({"primary": 0.75, "secondary": 0.8})


def test_partial_years_outside_range_are_dropped_and_missing_quarter_is_visible(spark):
    housing = [
        *quarters("primary", "transaction", "Opole", 2006, [3000] * 2),  # before 2007
        *quarters("primary", "transaction", "Opole", 2007, [3000] * 3),  # one quarter missing
    ]
    wages = [("Opole", 2006, 2500.0), ("Opole", 2007, 2900.0)]

    rows = run(spark, housing, wages).collect()

    assert [(r.year, r.quarters) for r in rows] == [(2007, 3)]
