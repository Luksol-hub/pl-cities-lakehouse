"""Point every table of the Power BI model at one data source: local Parquet files or Databricks.

The model, relationships and measures stay the same; only the Power Query (M) code that loads
each table changes. Run with Power BI Desktop CLOSED (it would overwrite the files).

    python scripts/set_powerbi_source.py databricks --host dbc-....cloud.databricks.com \
        --http-path /sql/1.0/warehouses/<id>
    python scripts/set_powerbi_source.py parquet

Databricks mode reads `pl_cities.gold.<table>` through a SQL warehouse with the "Databricks"
connector (`DatabricksMultiCloud.Catalogs`, for workspaces on AWS/GCP such as Free Edition;
Azure Databricks would use `Databricks.Catalogs`). Host and HTTP path are
model parameters (Power BI: Transform data -> Manage parameters), so they can be changed without
editing the queries. The access token is never stored here: Power BI asks for it on refresh.
"""

import argparse
import re
import uuid
from pathlib import Path

DEFINITION = Path("powerbi/pl-cities-report.SemanticModel/definition")
TABLES = DEFINITION / "tables"
EXPRESSIONS = DEFINITION / "expressions.tmdl"
GOLD_FOLDER = r"C:\projects\pl-cities-lakehouse\data\gold"
CATALOG, SCHEMA = "pl_cities", "gold"

PARQUET_M = (
    'Źródło = Parquet.Document(File.Contents("{folder}\\{table}.parquet"), '
    "[Compression=null, LegacyColumnNameEncoding=false, MaxDepth=null])"
)

def databricks_steps(table: str) -> list[str]:
    """Same navigation steps Power BI writes when you pick a table in the Databricks connector."""
    return [
        "Źródło = DatabricksMultiCloud.Catalogs(DatabricksHost, DatabricksHttpPath, "
        "[Catalog=null, Database=null, EnableAutomaticProxyDiscovery=null]),",
        f'katalog = Źródło{{[Name="{CATALOG}",Kind="Database"]}}[Data],',
        f'schemat = katalog{{[Name="{SCHEMA}",Kind="Schema"]}}[Data],',
        f'tabela = schemat{{[Name="{table}",Kind="Table"]}}[Data]',
    ]


def read_tmdl(path: Path) -> str:
    """TMDL files use CRLF; work on LF text in memory."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write_tmdl(path: Path, text: str) -> None:
    # Bytes, not text mode: Python text mode on Windows would turn \r\n into \r\r\n.
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def source_block(table: str, mode: str) -> str:
    """The `source =` block of a partition: a let ... in expression, indented as TMDL expects."""
    if mode == "parquet":
        steps, result = [PARQUET_M.format(folder=GOLD_FOLDER, table=table)], "Źródło"
    else:
        steps, result = databricks_steps(table), "tabela"
    lines = ["\t\tsource =", "\t\t\t\tlet"]
    lines += [f"\t\t\t\t    {step}" for step in steps]
    lines += ["\t\t\t\tin", f"\t\t\t\t    {result}"]
    return "\n".join(lines) + "\n"


def set_partition_source(text: str, table: str, mode: str) -> str:
    """Replace the source block of the table's partition (from `source =` to the blank line)."""
    pattern = re.compile(
        rf"(\tpartition {re.escape(table)} = m\n\t\tmode: import\n)\t\tsource =\n.*?\n(?=\n)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"partition source of {table} not found")
    return pattern.sub(lambda m: m.group(1) + source_block(table, mode), text, count=1)


def parameter(name: str, value: str, tag: str) -> str:
    return (
        f'expression {name} = "{value}" meta [IsParameterQuery=true, Type="Text", '
        "IsParameterQueryRequired=true]\n"
        f"\tlineageTag: {tag}\n\n"
        "\tannotation PBI_ResultType = Text\n\n"
    )


def write_parameters(host: str, http_path: str) -> None:
    """Create or update the two model parameters, keeping existing lineage tags."""
    old = read_tmdl(EXPRESSIONS) if EXPRESSIONS.exists() else ""
    tags = dict(re.findall(r"expression (\w+) = .*\n\tlineageTag: (\S+)", old))
    text = parameter("DatabricksHost", host, tags.get("DatabricksHost", str(uuid.uuid4())))
    text += parameter(
        "DatabricksHttpPath", http_path, tags.get("DatabricksHttpPath", str(uuid.uuid4()))
    )
    write_tmdl(EXPRESSIONS, text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["parquet", "databricks"])
    parser.add_argument("--host", help="server hostname of the SQL warehouse")
    parser.add_argument("--http-path", help="HTTP path of the SQL warehouse")
    args = parser.parse_args()

    if args.mode == "databricks":
        if not (args.host and args.http_path):
            parser.error("databricks mode needs --host and --http-path")
        write_parameters(args.host, args.http_path)

    for path in sorted(TABLES.glob("*.tmdl")):
        table = path.stem
        write_tmdl(path, set_partition_source(read_tmdl(path), table, args.mode))
        print(f"{table:20} -> {args.mode}")


if __name__ == "__main__":
    main()
