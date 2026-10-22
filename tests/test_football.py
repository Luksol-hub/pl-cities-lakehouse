from datetime import date

import pytest

from pl_cities_lakehouse.ingestion.football import (
    SCHEMA,
    parse_matches,
    read_records,
    to_dataframe,
)

# Same columns as the real file, shortened to what the parser reads plus one odds column.
CSV_TEXT = (
    "Country,League,Season,Date,Time,Home,Away,HG,AG,Res,AvgCH\n"
    "Poland,Ekstraklasa,2012/2013,17/08/2012,17:00,Pogon Szczecin,Zaglebie,4,0,H,3.01\n"
    "Poland,Ekstraklasa,2012/2013,18/08/2012,,Gornik Z.,Wisla,1,1,D,2.50\n"
)

TEAM_TOWNS = {
    "Pogon Szczecin": "Szczecin",
    "Zaglebie": "Lubin",
    "Gornik Z.": "Zabrze",
    "Wisla": "Kraków",
}


def test_parse_matches():
    records = parse_matches(CSV_TEXT, TEAM_TOWNS)

    assert records == [
        {
            "season": "2012/2013",
            "match_date": date(2012, 8, 17),
            "kickoff_time": "17:00",
            "home_team": "Pogon Szczecin",
            "away_team": "Zaglebie",
            "town": "Szczecin",
            "home_goals": 4,
            "away_goals": 0,
            "result": "H",
        },
        {
            "season": "2012/2013",
            "match_date": date(2012, 8, 18),
            "kickoff_time": None,
            "home_team": "Gornik Z.",
            "away_team": "Wisla",
            "town": "Zabrze",
            "home_goals": 1,
            "away_goals": 1,
            "result": "D",
        },
    ]


def test_parse_matches_fails_on_unknown_team():
    towns = {team: town for team, town in TEAM_TOWNS.items() if team != "Wisla"}

    with pytest.raises(ValueError, match="Wisla"):
        parse_matches(CSV_TEXT, towns)


def test_read_records_handles_byte_order_mark(tmp_path):
    path = tmp_path / "POL.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")

    records = read_records(path, TEAM_TOWNS)

    assert records[0]["season"] == "2012/2013"


def test_to_dataframe(spark):
    df = to_dataframe(spark, parse_matches(CSV_TEXT, TEAM_TOWNS), "POL.csv")

    assert df.count() == 2
    assert df.columns == [*SCHEMA.fieldNames(), "source_file", "ingested_at"]
