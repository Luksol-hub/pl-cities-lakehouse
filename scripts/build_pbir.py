"""Generate DAX measures (TMDL) and report pages/visuals (PBIR) for pl-cities-report.

The Power BI project in powerbi/ is plain text (PBIP), so measures, pages and visuals are
written here instead of clicked together. Pages are regenerated from scratch on every run,
so manual layout changes made in Power BI to those pages are overwritten.

Run with Power BI Desktop closed, from the repository root:
    python scripts/build_pbir.py powerbi
"""

import json
import re
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(sys.argv[1])
MODEL = ROOT / "pl-cities-report.SemanticModel" / "definition" / "tables"
REPORT = ROOT / "pl-cities-report.Report" / "definition"

VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

ACCENT = "#1F5A99"
NAVY = "#12355B"

# Report theme: light grey page, white rounded cards with a soft shadow, a palette of blues.
THEME_FILE = "pl-cities-theme.json"
THEME = {
    "name": "pl-cities",
    "dataColors": ["#1F5A99", "#4A7FB5", "#8DB3DA", "#12355B", "#6F9CC9", "#B8D2EC", "#2E7DBF", "#5E7C99"],
    "background": "#FFFFFF",
    "foreground": "#1F2937",
    "tableAccent": "#1F5A99",
    "good": "#1F5A99",
    "neutral": "#8DB3DA",
    "bad": "#C2410C",
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#1F2937"},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": "#1F2937"},
        "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#334155"},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 24, "color": "#1F5A99"},
    },
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": "#DCE3EC"}}, "radius": 10}],
            "dropShadow": [{"show": True, "color": {"solid": {"color": "#12355B"}}, "position": "Outer",
                            "preset": "BottomRight", "transparency": 88}],
            "visualHeader": [{"show": False}],
            "padding": [{"top": 8, "bottom": 8, "left": 10, "right": 10}],
        }},
        "page": {"*": {
            "background": [{"color": {"solid": {"color": "#EEF2F7"}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": "#EEF2F7"}}, "transparency": 0}],
        }},
        "textbox": {"*": {
            "background": [{"show": False}],
            "border": [{"show": False}],
            "dropShadow": [{"show": False}],
        }},
        "slicer": {"*": {
            "background": [{"show": False}],
            "border": [{"show": False}],
            "dropShadow": [{"show": False}],
        }},
        # Button slicer styled like the KPI cards: white rounded tiles with a soft shadow,
        # the selected tile filled with the accent colour.
        "advancedSlicerVisual": {"*": {
            "background": [{"show": False}],
            "border": [{"show": False}],
            "dropShadow": [{"show": False}],
            "shapeCustomRectangle": [{"$id": "default", "tileShape": "rectangleRoundedByPixel", "rectangleRoundedCurve": 10}],
            "fillCustom": [
                {"$id": "default", "show": True, "fillColor": {"solid": {"color": "#FFFFFF"}}, "transparency": 0},
                {"$id": "interaction:hover", "fillColor": {"solid": {"color": "#EEF4FB"}}},
                {"$id": "selection:selected", "fillColor": {"solid": {"color": "#1F5A99"}}},
            ],
            "value": [
                {"$id": "default", "show": True, "fontColor": {"solid": {"color": "#12355B"}}, "fontSize": 10, "bold": True},
                {"$id": "selection:selected", "fontColor": {"solid": {"color": "#FFFFFF"}}},
            ],
            "outline": [{"$id": "default", "show": True, "lineColor": {"solid": {"color": "#DCE3EC"}}, "weight": 1}],
            "shadowCustom": [{"$id": "default", "show": True, "color": {"solid": {"color": "#12355B"}},
                              "transparency": 88, "preset": "BottomRight"}],
        }},
    },
}

# ---------------------------------------------------------------- measures (TMDL)

MEASURES = {
    "mart_city_score": [
        ("Warunki życia", "AVERAGE(mart_city_score[quality_of_life_index])", "0.00"),
        (
            "m² za pensję",
            "VAR opt = SELECTEDVALUE(dim_market_option[option], \"Średnia z obu\") "
            "RETURN SWITCH(opt, "
            "\"Wtórny\", CALCULATE(AVERAGE(mart_city_score[m2_per_wage]), mart_city_score[market] = \"secondary\"), "
            "\"Pierwotny\", CALCULATE(AVERAGE(mart_city_score[m2_per_wage]), mart_city_score[market] = \"primary\"), "
            "AVERAGE(mart_city_score[m2_per_wage]))",
            "0.00",
        ),
        (
            "Cena za m²",
            "VAR opt = SELECTEDVALUE(dim_market_option[option], \"Średnia z obu\") "
            "RETURN SWITCH(opt, "
            "\"Wtórny\", CALCULATE(AVERAGE(mart_city_score[avg_price_pln_m2]), mart_city_score[market] = \"secondary\"), "
            "\"Pierwotny\", CALCULATE(AVERAGE(mart_city_score[avg_price_pln_m2]), mart_city_score[market] = \"primary\"), "
            "AVERAGE(mart_city_score[avg_price_pln_m2]))",
            "#,0",
        ),
        ("Pensja brutto", "AVERAGE(mart_city_score[wage_pln])", "#,0"),
        (
            "Ocena dostępności",
            "VAR cur = [m² za pensję] VAR lo = MINX(ALLSELECTED(dim_location[city]), [m² za pensję]) "
            "VAR hi = MAXX(ALLSELECTED(dim_location[city]), [m² za pensję]) "
            "RETURN IF(NOT ISBLANK(cur), IF(hi = lo, 1, DIVIDE(cur - lo, hi - lo)))",
            "0.00",
        ),
        (
            "Wynik końcowy",
            "IF(NOT ISBLANK([Warunki życia]), 0.5 * [Warunki życia] + 0.5 * [Ocena dostępności])",
            "0.00",
        ),
        (
            "Miejsce",
            "IF(NOT ISBLANK([Wynik końcowy]), RANKX(FILTER(ALLSELECTED(dim_location[city]), "
            "NOT ISBLANK([Wynik końcowy])), [Wynik końcowy], , DESC, Skip))",
            "0",
        ),
        (
            "Najlepszy wynik – miasto",
            "CONCATENATEX(TOPN(1, FILTER(VALUES(dim_location[city]), NOT ISBLANK([Wynik końcowy])), "
            "[Wynik końcowy], DESC), dim_location[city], \", \")",
            None,
        ),
        (
            "Najlepsze warunki – miasto",
            "CONCATENATEX(TOPN(1, FILTER(VALUES(dim_location[city]), NOT ISBLANK([Warunki życia])), "
            "[Warunki życia], DESC), dim_location[city], \", \")",
            None,
        ),
        (
            "Najwięcej m² – miasto",
            "CONCATENATEX(TOPN(1, FILTER(VALUES(dim_location[city]), NOT ISBLANK([m² za pensję])), "
            "[m² za pensję], DESC), dim_location[city], \", \")",
            None,
        ),
        (
            "Najmniej m² – miasto",
            "CONCATENATEX(TOPN(1, FILTER(VALUES(dim_location[city]), NOT ISBLANK([m² za pensję])), "
            "[m² za pensję], ASC), dim_location[city], \", \")",
            None,
        ),
    ],
    "dim_location": [
        ("Miasto", "SELECTEDVALUE(dim_location[city])", None),
        ("Województwo", "SELECTEDVALUE(dim_location[voivodeship])", None),
    ],
    "fact_weather_daily": [
        ("Dni z deszczem", "CALCULATE(COUNTROWS(fact_weather_daily), fact_weather_daily[precipitation_mm] >= 1)", "0"),
        ("Dni z mrozem", "CALCULATE(COUNTROWS(fact_weather_daily), fact_weather_daily[temp_mean_c] < 0)", "0"),
        ("Dni upalne", "CALCULATE(COUNTROWS(fact_weather_daily), fact_weather_daily[temp_mean_c] >= 22)", "0"),
    ],
    "fact_air_quality": [
        ("Dni smogu", "AVERAGE(fact_air_quality[days_pm10_over_50])", "0.0"),
    ],
    "fact_match": [
        ("Mecze", "COUNTROWS(fact_match)", "#,0"),
        ("Gole na mecz", "AVERAGEX(fact_match, fact_match[home_goals] + fact_match[away_goals])", "0.00"),
        ("Wygrane gospodarzy %", "DIVIDE(CALCULATE(COUNTROWS(fact_match), fact_match[result] = \"H\"), [Mecze])", "0.0%"),
        ("Remisy %", "DIVIDE(CALCULATE(COUNTROWS(fact_match), fact_match[result] = \"D\"), [Mecze])", "0.0%"),
        ("Wygrane gości %", "DIVIDE(CALCULATE(COUNTROWS(fact_match), fact_match[result] = \"A\"), [Mecze])", "0.0%"),
    ],
    "mart_match_weather": [
        ("Mecze w przedziale", "SUM(mart_match_weather[matches])", "#,0"),
        ("Gole w przedziale", "AVERAGE(mart_match_weather[avg_goals])", "0.00"),
        ("Wygrane gospodarzy w przedziale", "AVERAGE(mart_match_weather[home_win_share])", "0.0%"),
    ],
}


def tmdl_name(name: str) -> str:
    """TMDL quotes only names with spaces or other non-word characters; Power BI saves them that way."""
    return name if re.fullmatch(r"\w+", name) else f"'{name}'"


def read_tmdl(path: Path) -> str:
    # Bytes, not text mode: text mode on Windows rewrites line endings on its own.
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write_tmdl(path: Path, text: str) -> None:
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def add_measures(table: str, measures) -> None:
    path = MODEL / f"{table}.tmdl"
    text = read_tmdl(path)
    blocks = []
    for name, expr, fmt in measures:
        # Earlier runs may have written the name quoted even when Power BI saves it bare.
        quoted = f"\tmeasure '{name}' = "
        head = f"\tmeasure {tmdl_name(name)} = "
        if quoted != head and quoted in text and head in text:
            start = text.index(quoted)
            end = text.index("\n\n", start) + 2
            text = text[:start] + text[end:]
        elif quoted != head and quoted in text:
            text = text.replace(quoted, head, 1)
        if head in text:
            # Measure exists: replace its one-line expression, keep format and lineage tag.
            start = text.index(head)
            end = text.index("\n", start)
            text = text[:start] + head + expr + text[end:]
            continue
        lines = [f"\tmeasure {tmdl_name(name)} = {expr}"]
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        blocks.append("\n".join(lines) + "\n\n")
    marker = f"\tpartition {table} = m"
    if marker not in text:
        raise SystemExit(f"partition line not found in {path}")
    text = text.replace(marker, "".join(blocks) + marker, 1)
    write_tmdl(path, text)


MARKET_OPTION_TMDL = """table dim_market_option
\tlineageTag: {table_tag}

\tcolumn option
\t\tdataType: string
\t\tsortByColumn: option_order
\t\tlineageTag: {option_tag}
\t\tsummarizeBy: none
\t\tsourceColumn: option

\t\tannotation SummarizationSetBy = Automatic

\tcolumn option_order
\t\tdataType: int64
\t\tformatString: 0
\t\tlineageTag: {order_tag}
\t\tsummarizeBy: none
\t\tsourceColumn: option_order

\t\tannotation SummarizationSetBy = Automatic

\tcolumn market
\t\tdataType: string
\t\tlineageTag: {market_tag}
\t\tsummarizeBy: none
\t\tsourceColumn: market

\t\tannotation SummarizationSetBy = Automatic

\tpartition dim_market_option = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Źródło = Parquet.Document(File.Contents("C:\\projects\\pl-cities-lakehouse\\data\\gold\\dim_market_option.parquet"), [Compression=null, LegacyColumnNameEncoding=false, MaxDepth=null])
\t\t\t\tin
\t\t\t\t    Źródło

\tannotation PBI_ResultType = Table

"""


def add_market_option_table() -> None:
    """Disconnected slicer table (no relationships): measures read the selected option."""
    path = MODEL / "dim_market_option.tmdl"
    if not path.exists():
        tags = {k: uuid.uuid4() for k in ("table_tag", "option_tag", "order_tag", "market_tag")}
        write_tmdl(path, MARKET_OPTION_TMDL.format(**tags))
    model = MODEL.parent / "model.tmdl"
    text = read_tmdl(model)
    if "ref table dim_market_option" not in text:
        text = text.replace("ref table dim_location\n", "ref table dim_location\nref table dim_market_option\n", 1)
        write_tmdl(model, text)


def sort_bucket_by_order() -> None:
    path = MODEL / "mart_match_weather.tmdl"
    text = read_tmdl(path)
    old = "\tcolumn bucket\n\t\tdataType: string\n"
    if "sortByColumn: bucket_order" not in text:
        if old not in text:
            raise SystemExit("bucket column not found")
        text = text.replace(old, old + "\t\tsortByColumn: bucket_order\n", 1)
    write_tmdl(path, text)


# ---------------------------------------------------------------- PBIR helpers


def lit(value):
    """Literal expression: strings quoted, numbers as doubles, booleans as words."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_value):
    return {"solid": {"color": lit(hex_value)}}


def col(table, column):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}


def measure(table, name):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def proj(field, display=None):
    kind = "Column" if "Column" in field else "Measure"
    entity = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    p = {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def title(text, size=12):
    return {
        "title": [
            {
                "properties": {
                    "show": lit(True),
                    "text": lit(text),
                    "fontSize": lit(size),
                    "bold": lit(True),
                }
            }
        ]
    }


def container(name, x, y, w, h, visual, z=0, filters=None):
    data = {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
        "visual": visual,
    }
    if filters:
        data["filterConfig"] = {"filters": filters}
    return data


def textbox(paragraphs):
    return {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "drillFilterOtherVisuals": True,
    }


def run(text, size, bold=False, colour=NAVY):
    style = {"fontSize": f"{size}pt", "color": colour}
    if bold:
        style["fontWeight"] = "bold"
    return {"textRuns": [{"value": text, "textStyle": style}]}


def card(field, label, value_size=20, label_size=10):
    """KPI card like the inspiration report: small label on top, large blue value below."""
    return {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [proj(field, label)]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit(value_size), "color": color(ACCENT), "bold": lit(True)}}],
            "categoryLabels": [{"properties": {"show": lit(False)}}],
        },
        "visualContainerObjects": {
            "title": [{"properties": {
                "show": lit(label is not None),
                "text": lit(label or ""),
                "fontSize": lit(label_size),
                "bold": lit(True),
                "fontColor": color("#334155"),
            }}],
        },
        "drillFilterOtherVisuals": True,
    }


def install_theme() -> None:
    """Write the custom theme into the report and point report.json at it."""
    resources = REPORT.parent / "StaticResources" / "RegisteredResources"
    write_json(resources / THEME_FILE, THEME)

    report_path = REPORT / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    base = report["themeCollection"]["baseTheme"]
    report["themeCollection"]["customTheme"] = {
        "name": THEME_FILE,
        "reportVersionAtImport": base["reportVersionAtImport"],
        "type": "RegisteredResources",
    }
    packages = [p for p in report.get("resourcePackages", []) if p["name"] != "RegisteredResources"]
    packages.append({
        "name": "RegisteredResources",
        "type": "RegisteredResources",
        "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}],
    })
    report["resourcePackages"] = packages
    write_json(report_path, report)


def categorical_filter(name, table, column, value):
    return {
        "name": name,
        "field": col(table, column),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "f", "Entity": table, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": column}}
                            ],
                            "Values": [[{"Literal": {"Value": f"'{value}'"}}]],
                        }
                    }
                }
            ],
        },
    }


# ---------------------------------------------------------------- pages


def page_b():
    visuals = [container("b_title", 24, 4, 1100, 70, textbox([
        run("Czy pogoda zmienia wynik meczu?", 18, True),
        run("Ekstraklasa, sezony 2012/13–2025/26; pogoda dzienna w mieście, w którym grano mecz "
            "(z uwzględnieniem przenosin stadionów).", 9, False, "#475569"),
    ]), z=0)]

    cards = [
        ("b_card_matches", measure("fact_match", "Mecze"), "Mecze"),
        ("b_card_goals", measure("fact_match", "Gole na mecz"), "Gole na mecz"),
        ("b_card_home", measure("fact_match", "Wygrane gospodarzy %"), "Wygrane gospodarzy"),
        ("b_card_draw", measure("fact_match", "Remisy %"), "Remisy"),
    ]
    for i, (name, field, label) in enumerate(cards):
        visuals.append(container(name, 24 + i * 313, 80, 297, 88, card(field, label), z=1000 + i))

    for i, (factor, heading) in enumerate([("rain", "Deszcz"), ("temperature", "Temperatura"), ("wind", "Wiatr")]):
        bucket = col("mart_match_weather", "bucket")
        visual = {
            "visualType": "clusteredColumnChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [proj(bucket, "Przedział")]},
                    "Y": {"projections": [proj(measure("mart_match_weather", "Wygrane gospodarzy w przedziale"), "Wygrane gospodarzy")]},
                },
                "sortDefinition": {"sort": [{"field": bucket, "direction": "Ascending"}], "isDefaultSort": True},
            },
            "objects": {
                "dataPoint": [{"properties": {"fill": color(ACCENT)}}],
                "labels": [{"properties": {"show": lit(True)}}],
            },
            "visualContainerObjects": {
                **title(f"{heading}: % wygranych gospodarzy", 11),
                "subTitle": [{"properties": {"show": lit(False)}}],
            },
            "drillFilterOtherVisuals": True,
        }
        filters = [categorical_filter(f"b_filter_{factor}", "mart_match_weather", "factor", factor)]
        visuals.append(container(f"b_chart_{factor}", 24 + i * 413, 180, 397, 400, visual, z=2000 + i, filters=filters))

    visuals.append(container("b_conclusion", 24, 592, 1232, 116, textbox([
        run("Wniosek", 12, True),
        run("Pogoda w dniu meczu ma znikomy związek z wynikiem: korelacja z liczbą goli jest bliska zera "
            "(deszcz −0,006, temperatura 0,038, wiatr −0,013). Wyższy odsetek wygranych gospodarzy przy wietrze "
            "opiera się na 259 meczach i jest tropem, nie dowodem; przedział „wichura” ma tylko 2 mecze.", 11, False, "#334155"),
    ]), z=3000))

    page = {
        "$schema": PAGE_SCHEMA,
        "name": "pytanie_b",
        "displayName": "Pytanie B: pogoda a mecze",
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }
    return page, visuals


def page_tooltip():
    """City card shown on hover: name and voivodeship on top, a grid of small KPI tiles below."""
    visuals = [
        container("t_city", 8, 8, 200, 60, card(measure("dim_location", "Miasto"), None, 18), z=0),
        container("t_region", 214, 8, 138, 60, card(measure("dim_location", "Województwo"), "Województwo", 10, 8), z=1),
    ]
    tiles = [
        ("t_rank", measure("mart_city_score", "Miejsce"), "Miejsce"),
        ("t_score", measure("mart_city_score", "Wynik końcowy"), "Wynik końcowy"),
        ("t_qol", measure("mart_city_score", "Warunki życia"), "Warunki życia"),
        ("t_m2", measure("mart_city_score", "m² za pensję"), "m² za pensję"),
        ("t_smog", measure("fact_air_quality", "Dni smogu"), "Dni smogu"),
        ("t_rain", measure("fact_weather_daily", "Dni z deszczem"), "Dni z deszczem"),
        ("t_price", measure("mart_city_score", "Cena za m²"), "Cena za m² (zł)"),
        ("t_wage", measure("mart_city_score", "Pensja brutto"), "Pensja brutto (zł)"),
    ]
    for i, (name, field, label) in enumerate(tiles):
        x = 8 + (i % 2) * 175
        y = 76 + (i // 2) * 62
        visuals.append(container(name, x, y, 169, 56, card(field, label, 14, 8), z=10 + i))
    page = {
        "$schema": PAGE_SCHEMA,
        "name": "tooltip_miasto",
        "displayName": "Tooltip: miasto",
        "displayOption": "ActualSize",
        "height": 330,
        "width": 360,
        "type": "Tooltip",
        "visibility": "HiddenInViewMode",
        "pageBinding": {"name": str(uuid.uuid4()), "type": "Tooltip"},
    }
    return page, visuals


def tile_slicer(field, display, default=None, values_filter=None):
    """Horizontal tile slicer (one button per value), single select, optional default value."""
    general = {"orientation": lit(1)}
    if default is not None:
        table = field["Column"]["Expression"]["SourceRef"]["Entity"]
        column = field["Column"]["Property"]
        general["filter"] = {"filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": column}}],
                "Values": [[{"Literal": {"Value": default}}]],
            }}}],
        }}
    return {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [proj(field, display)]}}},
        "objects": {
            "data": [{"properties": {"mode": lit("Basic")}}],
            "general": [{"properties": general}],
            "selection": [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(True)}}],
            "items": [{"properties": {
                "fontSize": lit(10),
                "fontColor": color(NAVY),
                "background": color("#FFFFFF"),
                "outline": lit("Frame"),
                "outlineColor": color("#C9D6E5"),
            }}],
            "header": [{"properties": {"show": lit(False)}}],
        },
        "drillFilterOtherVisuals": True,
    }


def button_slicer(field, display, default):
    """New button slicer (advancedSlicerVisual), single select; its look comes from the theme."""
    table = field["Column"]["Expression"]["SourceRef"]["Entity"]
    column = field["Column"]["Property"]
    return {
        "visualType": "advancedSlicerVisual",
        "query": {"queryState": {"Values": {"projections": [proj(field, display)]}}},
        "objects": {
            "selection": [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(True)}}],
            "general": [{"properties": {"filter": {"filter": {
                "Version": 2,
                "From": [{"Name": "s", "Entity": table, "Type": 0}],
                "Where": [{"Condition": {"In": {
                    "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": column}}],
                    "Values": [[{"Literal": {"Value": default}}]],
                }}}],
            }}}}],
        },
        "visualContainerObjects": {"title": [{"properties": {"show": lit(False)}}]},
        "drillFilterOtherVisuals": True,
    }


def year_slider(field, display, default_year):
    """Slider (range slicer) with both handles on `default_year`; widening it averages the years."""
    table = field["Column"]["Expression"]["SourceRef"]["Entity"]
    column = field["Column"]["Property"]
    ref = {"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": column}}
    year_literal = {"Literal": {"Value": f"{default_year}L"}}
    between = {"And": {
        # ComparisonKind 2 = greater than or equal, 4 = less than or equal.
        "Left": {"Comparison": {"ComparisonKind": 2, "Left": ref, "Right": year_literal}},
        "Right": {"Comparison": {"ComparisonKind": 4, "Left": ref, "Right": year_literal}},
    }}
    return {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [proj(field, display)]}}},
        "objects": {
            "data": [{"properties": {"mode": lit("Between")}}],
            "general": [{"properties": {"filter": {"filter": {
                "Version": 2,
                "From": [{"Name": "s", "Entity": table, "Type": 0}],
                "Where": [{"Condition": between}],
            }}}}],
            # No header: the theme's padding leaves too little height for header, inputs and slider bar.
            "header": [{"properties": {"show": lit(False)}}],
            "slider": [{"properties": {"show": lit(True), "color": color(ACCENT)}}],
            "numericInputStyle": [{"properties": {"fontColor": color(NAVY), "textSize": lit(10)}}],
        },
        "drillFilterOtherVisuals": True,
    }


def years_filter(name, first, last):
    """Visual-level filter that keeps only `first`..`last` years in the year slicer."""
    return {
        "name": name,
        "field": col("dim_date", "year"),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "y", "Entity": "dim_date", "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "y"}}, "Property": "year"}}],
                "Values": [[{"Literal": {"Value": f"{y}L"}}] for y in range(first, last + 1)],
            }}}],
        },
    }


def page_a():
    city = col("dim_location", "city")
    year = col("dim_date", "year")
    qol = measure("mart_city_score", "Warunki życia")
    m2 = measure("mart_city_score", "m² za pensję")
    score = measure("mart_city_score", "Wynik końcowy")
    rank = measure("mart_city_score", "Miejsce")
    smog = measure("fact_air_quality", "Dni smogu")
    visuals = []

    visuals.append(container("a_title", 24, 4, 530, 84, textbox([
        run("Gdzie najlepiej mieszkać?", 18, True),
        run("Warunki życia (pogoda + smog) kontra m² mieszkania za przeciętną pensję brutto. "
            "Najedź na miasto na wykresie, by zobaczyć szczegóły.", 9, False, "#475569"),
    ]), z=0))

    slider = year_slider(year, "Rok", 2025)
    visuals.append(container("a_slicer_year", 566, 4, 260, 88, slider, z=1001,
                             filters=[years_filter("a_filter_years", 2007, 2025)]))

    market = button_slicer(col("dim_market_option", "option"), "Rynek", default="'Wtórny'")
    visuals.append(container("a_slicer_market", 836, 14, 420, 70, market, z=1000))

    cards = [
        ("a_card_best", measure("mart_city_score", "Najlepszy wynik – miasto"), "Najlepszy wynik końcowy"),
        ("a_card_qol", measure("mart_city_score", "Najlepsze warunki – miasto"), "Najlepsze warunki życia"),
        ("a_card_most", measure("mart_city_score", "Najwięcej m² – miasto"), "Najwięcej m² za pensję"),
        ("a_card_least", measure("mart_city_score", "Najmniej m² – miasto"), "Najmniej m² za pensję"),
    ]
    for i, (name, field, label) in enumerate(cards):
        visual = card(field, label)
        visuals.append(container(name, 24 + i * 313, 98, 297, 80, visual, z=3000 + i))

    scatter = {
        "visualType": "scatterChart",
        "query": {"queryState": {
            "Category": {"projections": [proj(city, "Miasto")]},
            "X": {"projections": [proj(qol)]},
            "Y": {"projections": [proj(m2)]},
        }},
        "objects": {
            "dataPoint": [{"properties": {"fill": color(ACCENT)}}],
            "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(9)}}],
        },
        "visualContainerObjects": {
            **title("Warunki życia a dostępność mieszkań (prawy górny róg = dobrze w obu)", 11),
            "subTitle": [{"properties": {"show": lit(False)}}],
            "visualTooltip": [{"properties": {"type": lit("ReportPage"), "section": lit("tooltip_miasto")}}],
        },
        "drillFilterOtherVisuals": True,
    }
    visuals.append(container("a_scatter", 24, 186, 600, 318, scatter, z=4000))

    def colour_scale(field, low, high):
        queryref = f"{field['Measure']['Expression']['SourceRef']['Entity']}.{field['Measure']['Property']}"
        return {
            "properties": {
                "backColor": {"solid": {"color": {"expr": {"FillRule": {
                    "Input": field,
                    "FillRule": {"linearGradient2": {
                        "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
                        "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
                        "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
                    }},
                }}}}},
            },
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": queryref},
        }

    def width(field, px):
        kind = "Measure" if "Measure" in field else "Column"
        queryref = f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"
        return {"properties": {"value": lit(px)}, "selector": {"metadata": queryref}}

    table = {
        "visualType": "tableEx",
        "query": {
            "queryState": {"Values": {"projections": [
                proj(rank, "#"),
                proj(city, "Miasto"),
                proj(qol, "Warunki"),
                proj(m2, "m²/pensja"),
                proj(score, "Wynik"),
            ]}},
            "sortDefinition": {"sort": [{"field": rank, "direction": "Ascending"}], "isDefaultSort": True},
        },
        "objects": {
            "values": [
                {"properties": {
                    "fontSize": lit(10),
                    "fontColorPrimary": color("#0F172A"),
                    "backColorPrimary": color("#FFFFFF"),
                    "backColorSecondary": color("#F8FAFC"),
                }},
                colour_scale(qol, "#EEF4FB", "#8DB3DA"),
                colour_scale(m2, "#F2F5F9", "#AFC4DB"),
                {
                    "properties": {"dataBars": {
                        "positiveColor": color(ACCENT),
                        "negativeColor": color("#C2410C"),
                        "axisColor": color("#94A3B8"),
                        "reverseDirection": lit(False),
                        "hideText": lit(False),
                    }},
                    "selector": {"metadata": "mart_city_score.Wynik końcowy"},
                },
            ],
            "columnHeaders": [{"properties": {
                "fontSize": lit(9),
                "bold": lit(True),
                "fontColor": color("#475569"),
                "backColor": color("#FFFFFF"),
            }}],
            "grid": [{"properties": {
                "gridVertical": lit(False),
                "gridHorizontal": lit(True),
                "gridHorizontalColor": color("#E2E8F0"),
                "rowPadding": lit(3),
                "outlineColor": color("#E2E8F0"),
            }}],
            "columnWidth": [
                width(rank, 34), width(city, 150), width(qol, 90), width(m2, 90), width(score, 220),
            ],
            "total": [{"properties": {"totals": lit(False)}}],
        },
        "visualContainerObjects": title("Ranking końcowy (50% warunki + 50% dostępność)", 11),
        "drillFilterOtherVisuals": True,
    }
    visuals.append(container("a_table", 636, 186, 620, 318, table, z=5000))

    def line_chart(name, x, w, value, heading):
        # One accent area: the average of the 17 cities, or the city clicked in the table/scatter.
        visual = {
            "visualType": "areaChart",
            "query": {"queryState": {
                "Category": {"projections": [proj(year, "Rok")]},
                "Y": {"projections": [proj(value)]},
            }},
            "objects": {
                "dataPoint": [{"properties": {"fill": color(ACCENT)}}],
                "lineStyles": [{"properties": {"strokeWidth": lit(3), "showMarker": lit(True)}}],
                "legend": [{"properties": {"show": lit(False)}}],
                "labels": [{"properties": {"show": lit(False)}}],
            },
            "visualContainerObjects": {
                **title(heading, 11),
                "subTitle": [{"properties": {"show": lit(False)}}],
            },
            "drillFilterOtherVisuals": True,
        }
        return container(name, x, 512, w, 200, visual, z=6000 + x)

    visuals.append(line_chart("a_line_m2", 24, 616, m2, "m² za pensję 2007–2025: średnia miast (kliknij miasto, by zobaczyć jego przebieg)"))
    visuals.append(line_chart("a_line_smog", 652, 604, smog, "Dni smogu (PM10 > 50 µg/m³) 2007–2025: średnia miast"))

    # Line charts show the whole period: the year slicer does not filter them, and clicking a line
    # (city + year) does not filter the rest of the page, which would clash with the chosen year.
    others = ["a_scatter", "a_table", "a_card_best", "a_card_qol", "a_card_most", "a_card_least"]
    lines = ["a_line_m2", "a_line_smog"]
    interactions = [{"source": "a_slicer_year", "target": t, "type": "NoFilter"} for t in lines]
    interactions += [{"source": s, "target": t, "type": "NoFilter"} for s in lines for t in others + lines if s != t]
    # Clicking a city in the table or the scatter shows its line in the time charts (default filter),
    # highlights it in the scatter, and leaves the KPI cards and the ranking table untouched.
    cards = ["a_card_best", "a_card_qol", "a_card_most", "a_card_least"]
    interactions += [{"source": "a_table", "target": "a_scatter", "type": "HighlightFilter"}]
    interactions += [{"source": s, "target": t, "type": "NoFilter"} for s in ("a_table", "a_scatter") for t in cards]
    interactions += [{"source": "a_scatter", "target": "a_table", "type": "NoFilter"}]

    page = {
        "$schema": PAGE_SCHEMA,
        "name": "pytanie_a",
        "displayName": "Pytanie A: ranking miast",
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
        "visualInteractions": interactions,
    }
    return page, visuals


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    install_theme()
    add_market_option_table()
    for table, measures in MEASURES.items():
        add_measures(table, measures)
    sort_bucket_by_order()

    pages_dir = REPORT / "pages"
    # The empty default page created by Power BI is replaced by the two report pages.
    for old in pages_dir.iterdir():
        if old.is_dir() and old.name not in {"pytanie_a", "pytanie_b", "tooltip_miasto"}:
            shutil.rmtree(old)

    order = []
    for builder in (page_a, page_b, page_tooltip):
        page, visuals = builder()
        folder = pages_dir / page["name"]
        if folder.exists():
            shutil.rmtree(folder)
        write_json(folder / "page.json", page)
        for visual in visuals:
            write_json(folder / "visuals" / visual["name"] / "visual.json", visual)
        order.append(page["name"])
        print(f"{page['name']}: {len(visuals)} visuals")

    write_json(pages_dir / "pages.json", {"$schema": PAGES_SCHEMA, "pageOrder": order, "activePageName": "pytanie_a"})


if __name__ == "__main__":
    main()
