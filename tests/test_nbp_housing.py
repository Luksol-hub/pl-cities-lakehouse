import openpyxl
import pytest

from pl_cities_lakehouse.ingestion import nbp_housing
from pl_cities_lakehouse.ingestion.nbp_housing import (
    EXPECTED_CITIES,
    SCHEMA,
    parse_quarter,
    parse_sheet,
    read_records,
    to_dataframe,
)

CITIES = sorted(EXPECTED_CITIES)
MEANS = ["7 miast", "10 miast", "6 miast bez Warszawy"]


def block_header(cities):
    return ["Kwartał", *cities, *MEANS]


def make_rows(cities=CITIES, gdynia_label="Gdynia*", title_offset=1):
    """Mimic the NBP layout: an offer block, a gap, a transaction block, a hedonic block.

    `title_offset` places the transaction title above the first city (1) or above
    the "Kwartał" column (0); the real file uses both.
    """
    named = [gdynia_label if c == "Gdynia" else c for c in cities]
    width = len(named) + len(MEANS) + 1
    gap = [None, None]
    offer_start, trans_start = 0, width + len(gap)
    hedonic_start = trans_start + width + len(gap)

    titles = [None] * (hedonic_start + width)
    titles[offer_start + 1] = "Ceny ofertowe"
    titles[trans_start + title_offset] = "Ceny transakcyjne"
    titles[hedonic_start + 1] = "Indeks hedoniczny ceny m kw. mieszkań"

    header = block_header(named) + gap + block_header(named) + gap + block_header(named)

    def data_row(label, base, missing=()):
        prices = [None if c in missing else base + i for i, c in enumerate(cities)]
        block = [label, *prices, 9999.0, 9999.0, 9999.0]
        hedonic = [label, *[1.01] * len(cities), 1.0, 1.0, 1.0]
        return block + gap + [label, *[p and p + 100 for p in prices], 1, 1, 1] + gap + hedonic

    return [
        ("Rynek pierwotny",),
        ("PLN/1 sq.m",),
        tuple(titles),
        tuple(header),
        tuple(data_row("III 2006", 5000, missing={"Opole"})),
        tuple(data_row("IV 2006", 6000)),
        ("* Gdynia footnote",),
    ]


def test_parse_quarter():
    assert parse_quarter("III 2006") == (2006, 3)
    assert parse_quarter("I 2026") == (2026, 1)


@pytest.mark.parametrize("title_offset", [0, 1])
def test_parse_sheet_returns_city_prices_only(title_offset):
    records = parse_sheet(make_rows(title_offset=title_offset), "primary")

    # 2 price types x 2 quarters x 17 cities, minus Opole missing in one quarter of each block.
    assert len(records) == 2 * 2 * 17 - 2
    assert {r["price_type"] for r in records} == {"offer", "transaction"}
    assert {r["city"] for r in records} == EXPECTED_CITIES
    assert all(r["price_pln_m2"] < 9999 for r in records), "means must be skipped"


def test_parse_sheet_values():
    records = parse_sheet(make_rows(), "primary")
    by_key = {(r["price_type"], r["city"], r["year"], r["quarter"]): r for r in records}

    first_city = CITIES[0]
    assert by_key[("offer", first_city, 2006, 4)]["price_pln_m2"] == 6000.0
    assert by_key[("transaction", first_city, 2006, 4)]["price_pln_m2"] == 6100.0
    assert ("offer", "Opole", 2006, 3) not in by_key
    assert by_key[("offer", "Gdynia", 2006, 4)]["market"] == "primary"


def test_parse_sheet_fails_when_city_missing():
    rows = make_rows(cities=[c for c in CITIES if c != "Kraków"])
    with pytest.raises(ValueError, match="Kraków"):
        parse_sheet(rows, "primary")


def test_read_records_from_workbook(tmp_path):
    path = tmp_path / "ceny_mieszkan.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active.title = "Opis danych (data description)"
    for sheet in nbp_housing.SHEETS:
        ws = workbook.create_sheet(sheet)
        for row in make_rows():
            ws.append(list(row))
    workbook.save(path)

    records = read_records(path)

    assert {r["market"] for r in records} == {"primary", "secondary"}
    assert len(records) == 2 * (2 * 2 * 17 - 2)


def test_to_dataframe_schema(spark):
    records = parse_sheet(make_rows(), "primary")

    df = to_dataframe(spark, records, "ceny_mieszkan.xlsx")

    assert df.count() == len(records)
    assert df.columns == [*SCHEMA.fieldNames(), "source_file", "ingested_at"]
