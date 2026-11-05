# pl-cities-lakehouse: notes for Claude

Portfolio project for data engineering job interviews. The owner works alone, writes in Polish
and is learning; answers go in Polish, code and commit messages in English.

## Working agreements

- Explain every step in plain Polish: what changes, in which file (full path), and why.
  Explain jargon on first use and tie concepts to likely interview questions.
- Backend (ingestion, Spark, data model): small steps, one piece at a time, then wait.
  Claude may write the code but explains it line by line.
- Power BI report visuals: Claude builds them (`scripts/build_pbir.py`); the owner only tweaks layout.
- Git is done by the owner. Commit straight to `main` (no feature branches). Claude does not run
  `git add/commit/push/pull`; it lists changed files and suggests a commit message.
- Add every new interview-relevant concept to `docs/interview-notes.md` (Polish, same style).
- Current status and next steps: `docs/progress.md`. Keep it updated at the end of a work session.

## Commands (PowerShell, repository root)

```powershell
.\.venv\Scripts\Activate.ps1
pytest                                  # ~1-2 min on Windows (Spark start-up)
ruff check .
python -m pl_cities_lakehouse.export_gold          # raw files -> gold Parquet in data/gold
python scripts/build_pbir.py powerbi               # measures + report pages; Power BI Desktop CLOSED
```

Raw data lives in `data/raw/` (git-ignored); download functions are in each `ingestion/*.py` module.

## Layout

- `src/pl_cities_lakehouse/ingestion/`: bronze, one module per source (nbp_housing, open_meteo,
  gus_bdl, gios, football). Plain Python parses files; `to_dataframe` builds the Spark table + metadata.
- `src/pl_cities_lakehouse/transformations/`: `silver_*` (quality checks, business rules) and
  `gold_*` (indices, ranking, star schema dimensions and facts).
- `src/pl_cities_lakehouse/common/`: cities, teams (stadium towns, relocations), Spark session, quality checks.
- `src/pl_cities_lakehouse/export_gold.py`: whole pipeline in memory, gold tables to Parquet for Power BI.
- `powerbi/`: Power BI project (PBIP, PBIR + TMDL text files).
- `docs/`: plan, index definition, module B findings, Power BI model, interview notes, progress.

## Gotchas

- Spark on Windows cannot write files (no winutils): pipeline runs in memory; Delta writes come with Databricks.
- Every function takes and returns a DataFrame, so the same code runs locally, in tests and on Databricks.
- `pandas<3`: PySpark 4 does not fully support pandas 3.
- Spark is strict about types: `14000` is rejected in a double column, use `14000.0`.
- Power BI TMDL files use CRLF; write them as bytes (Python text mode on Windows doubles `\r`).
- Edit `powerbi/` files only while Power BI Desktop is closed, or it overwrites the changes.
- `build_pbir.py` regenerates pages from scratch: manual layout changes in Power BI are lost.
- TMDL quotes object names only when they contain spaces or special characters (`Mecze`, but `'Wynik końcowy'`).
- New tables added through files are empty until Power BI Desktop refreshes; refresh before publishing.
- Model published to Fabric workspace `pl-cities-lakehouse` (model `pl-cities-report`); the Power BI MCP server
  connects with `ConnectFabric` and can run DAX queries to verify measures.
- Slider/button slicer styling: the button slicer (`advancedSlicerVisual`) is styled in the theme
  (`pl-cities-theme.json`); the range slicer needs room (no header) or its slider bar is clipped.
