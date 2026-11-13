# Postęp projektu

Stan na 2026-11-05. Szczegóły planu: [plan.md](plan.md), definicje wskaźników: [quality-of-life-index.md](quality-of-life-index.md).

## Gotowe (lokalnie, z testami: 83 testy, CI zielone)

| Warstwa | Co jest | Gdzie |
| --- | --- | --- |
| Bronze | 5 źródeł: ceny NBP (Excel), pogoda Open-Meteo (API, 34 miejscowości, 2006–2026), zarobki GUS BDL (API z paginacją), PM10 GIOŚ (Excel), mecze Ekstraklasy (CSV) | `ingestion/` |
| Silver | kontrole jakości (`common/quality.py`), PM10: kompletność ≥ 75%, metoda 24g przed 1g, mediana ze stacji; mecze połączone z pogodą, z przenosinami stadionów | `transformations/silver_*` |
| Gold | wskaźnik warunków życia, m² za pensję (rynki osobno), ranking `mart_city_score`, moduł B `mart_match_weather`, model gwiazdy (`dim_date`, `dim_location`, `dim_team` SCD2, `dim_market_option`, 5 faktów) | `transformations/gold_*` |
| Eksport | cały pipeline w pamięci → `data/gold/*.parquet` | `export_gold.py` |
| Power BI | model z relacjami, 25 miar DAX, motyw (jasne tło, białe karty, niebieska paleta), strony „Pytanie A” i „Pytanie B” (1280×720) + tooltip „karta miasta” | `powerbi/`, `scripts/build_pbir.py` |
| Fabric | model opublikowany do obszaru `pl-cities-lakehouse` (model `pl-cities-report`); MCP Power BI łączy się przez `ConnectFabric` i uruchamia zapytania DAX | – |

## Strona A w Power BI (stan obecny)

- suwak roku (fragmentator zakresu; oba uchwyty na jednym roku = ranking tego roku, rozsunięte = średnia lat),
- przyciski rynku Wtórny / Pierwotny / Średnia z obu (fragmentator przycisków stylizowany w motywie),
- 4 karty KPI, wykres punktowy z tooltipem, tabela rankingu z kolorami komórek i paskami,
- wykresy obszarowe w czasie: średnia miast albo miasto kliknięte w tabeli lub na wykresie punktowym.

## Najważniejsze decyzje

- Wskaźnik warunków życia: 50% pogoda (deszcz 40 / mróz 40 / upał 20) + 50% PM10; min-max w obrębie roku.
- Ranking: 50% warunki + 50% dostępność; miasto bez PM10 w danym roku pomijane.
- Rynki osobno; wybór rynku w Power BI przez tabelę rozłączoną `dim_market_option` i miary z `SWITCH`.
- Spark lokalnie tylko w pamięci; zapis do Delta na Databricks.
- Commity robi właściciel, prosto na `main`.

## Weryfikacja

Ranking 2025 sprawdzony przez MCP (DAX w opublikowanym modelu) dla wszystkich trzech opcji rynku; zgadza się z gold:
wtórny – Szczecin 0,64; pierwotny – Zielona Góra 0,80; średnia – Zielona Góra 0,72; ostatni zawsze Kraków.

## Do zrobienia: Power BI (opcjonalnie)

- [ ] Domyślne ustawienie suwaka (2025) i rynku (Wtórny) zapisywane przez skrypt: obecnie trzeba je ustawić w Power BI przed zapisem.
- [ ] Mapa Polski z bąblami (współrzędne są w `dim_location`); wymaga włączenia wizualizacji map w opcjach Power BI.
- [ ] Polskie nazwy przedziałów pogody na stronie B (obecnie np. „calm (< 30 km/h)”).
- Mockup referencyjny: artefakt „PL Cities Report Mockup” (claude.ai).

## Do zrobienia: chmura

Darmowe konto Azure niedostępne (2026-11-13, „not eligible” na luksolarski@outlook.com; konto służbowe
ValueTank nie jest używane). Decyzja: Databricks Free Edition teraz, Fabric na porównanie. Szczegóły w [plan.md](plan.md).

- [x] Konto Databricks Free Edition (2026-11-13); notebook serverless pobiera dane z Open-Meteo (HTTP 200),
  więc moduły `ingestion` mogą działać w chmurze.
- [x] Unity Catalog: katalog `pl_cities`, schematy `raw` / `bronze` / `silver` / `gold`,
  wolumin `pl_cities.raw.files` na surowe pliki.
- [x] Kod z repo w Databricks: Git folder `pl-cities-lakehouse` (gałąź `main`), import paczki działa
  (17 miast). Obieg: kod lokalnie → `git push` → Pull w Git folderze → uruchomienie.
- [ ] Notebook `notebooks/01_bronze_weather.py`: JSON z Open-Meteo do woluminu, tabela Delta
  `pl_cities.bronze.weather_daily` (na razie pełne nadpisanie).
- [ ] Zapis warstw do Delta; MERGE dla przyrostowego ładowania pogody.
- [ ] Orkiestracja (Databricks Workflows), alert przy błędzie.
- [ ] Power BI na danych z Databricks lub Fabric (zmiana źródła; model i miary zostają).
- [ ] Tydzień 8: porównanie Databricks i Fabric, tabela kosztów w README.
- [ ] Opcjonalnie: Azure pay-as-you-go (ADLS Gen2, Azure Databricks) na krótko, z budżetem.
