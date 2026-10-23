import pytest

from pl_cities_lakehouse.transformations.gold_city_score import gold_city_score

QOL_SCHEMA = "city string, year int, quality_of_life_index double"
AFF_SCHEMA = (
    "market string, city string, year int, avg_price_pln_m2 double, wage_pln double,"
    " m2_per_wage double"
)


def run(spark, qol_rows, aff_rows):
    return gold_city_score(
        spark.createDataFrame(qol_rows, QOL_SCHEMA),
        spark.createDataFrame(aff_rows, AFF_SCHEMA),
    )


def aff(market, city, year, m2_per_wage):
    return (market, city, year, 10000.0, 10000.0 * m2_per_wage, m2_per_wage)


def test_final_score_and_ranks(spark):
    # A: best place to live, least affordable. C: worst place to live, most affordable.
    qol = [("A", 2025, 1.0), ("B", 2025, 0.6), ("C", 2025, 0.0)]
    affordability = [
        aff("secondary", "A", 2025, 0.7),
        aff("secondary", "B", 2025, 0.9),
        aff("secondary", "C", 2025, 1.1),
    ]

    rows = {r.city: r for r in run(spark, qol, affordability).collect()}

    assert rows["A"].affordability_score == pytest.approx(0.0)
    assert rows["B"].affordability_score == pytest.approx(0.5)
    assert rows["C"].affordability_score == pytest.approx(1.0)
    assert rows["B"].final_score == pytest.approx(0.55)  # 0.5 * 0.6 + 0.5 * 0.5
    assert {c: rows[c].final_rank for c in "ABC"} == {"B": 1, "A": 2, "C": 2}
    assert {c: rows[c].quality_of_life_rank for c in "ABC"} == {"A": 1, "B": 2, "C": 3}
    assert {c: rows[c].affordability_rank for c in "ABC"} == {"C": 1, "B": 2, "A": 3}


def test_markets_are_ranked_separately(spark):
    qol = [("A", 2025, 0.5), ("B", 2025, 0.5)]
    affordability = [
        aff("primary", "A", 2025, 0.9),  # A wins on the primary market
        aff("primary", "B", 2025, 0.7),
        aff("secondary", "A", 2025, 0.8),
        aff("secondary", "B", 2025, 1.0),  # B wins on the secondary market
    ]

    ranks = {(r.market, r.city): r.final_rank for r in run(spark, qol, affordability).collect()}

    assert ranks == {
        ("primary", "A"): 1,
        ("primary", "B"): 2,
        ("secondary", "A"): 2,
        ("secondary", "B"): 1,
    }


def test_city_without_quality_of_life_index_is_left_out(spark):
    qol = [("Kraków", 2007, 0.2)]
    affordability = [aff("primary", "Kraków", 2007, 0.4), aff("primary", "Opole", 2007, 0.7)]

    assert [r.city for r in run(spark, qol, affordability).collect()] == ["Kraków"]
