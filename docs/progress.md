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
- [x] Notebook `notebooks/01_bronze_weather.py`: JSON z Open-Meteo do woluminu, tabela Delta
  `pl_cities.bronze.weather_daily` (pełne nadpisanie). Sprawdzone 2026-11-13: 34 miejscowości
  × 7305 dni (2006-07-01 – 2026-06-30).
- [x] MERGE dla przyrostowego ładowania pogody, sprawdzone w Databricks 2026-11-17: wersja 1 dopisała
  135 dni na miasto (do 2026-11-12, 7440 dni), wersja 2 (ponowne uruchomienie) zaktualizowała
  238 wierszy (34 × 7 dni lookbacku), liczba dni bez zmian, więc ładowanie jest idempotentne.
  `open_meteo.incremental_ranges` (od tygodnia przed ostatnim dniem do dziś − 5 dni, bo archiwum ma
  opóźnienie), `save_increments` (pliki `<miasto>_<od>_<do>.json` w `increments/`),
  `common/delta.merge_into` (MERGE po `city` + `date`). Notebook: pełne ładowanie tylko przy pierwszym
  uruchomieniu, potem zawsze przyrost.
- [x] Pozostałe źródła w bronze: notebook `notebooks/02_bronze_snapshots.py`, uruchomiony 2026-11-17 bez błędów
  (GIOŚ i GUS odpowiadają z Databricks); w `pl_cities.bronze` jest 5 tabel.
  Źródła publikują całą historię w każdym pliku, więc pełne nadpisanie tabel `housing_prices`, `wages`,
  `pm10`, `matches`; surowe pliki w woluminie w folderach z datą ładowania.
- [x] Silver i gold jako tabele Delta: notebook `notebooks/03_silver_gold.py`, uruchomiony 2026-11-17
  (5 tabel silver, 11 gold; `fact_weather_daily` 252 960 wierszy, `dim_date` do 2026-11-12).
  Ranking 2025 w chmurze różni się lekko od lokalnego (Szczecin wtórny 0,634 zamiast 0,642; liderzy ci sami).
  Przyczyna: Open-Meteo przeliczyło archiwum między pobraniem lokalnym (2026-10-22) a chmurowym
  (2026-11-13): średnia temperatura różni się do 0,4°C w ok. 220 dniach 2025, wiatr w ok. 45, opady bez zmian;
  to zmienia liczbę dni z mrozem/upałem. Ceny NBP i zarobki 2025 bez zmian; NBP dodał III kw. 2026 (+68 wierszy).
  Do wyjaśnienia (drobne): affordability_score różni się o ok. 0,0002.
  Wspólna logika w `pipeline.py` (`silver_tables`, `gold_tables`), z której korzysta też lokalny
  `export_gold.py`; kalendarz `dim_date` sięga do ostatniego dnia pogody.
- [x] Orkiestracja: job `pl-cities-daily` w Databricks Workflows (2026-11-17). DAG: `bronze_weather` i
  `bronze_snapshots` równolegle (ponowienia 3×) → `silver_gold`. Codziennie 06:00 Europe/Warsaw, mail przy
  błędzie. Pierwsze uruchomienie ręczne: sukces w 2 min 12 s. Źródło zadań: Git (repo z GitHuba, gałąź
  `main`, ścieżki względne `notebooks/...`; konto GitHub podpięte w Settings → Linked accounts), więc każde
  uruchomienie bierze najnowszy kod z `main` bez ręcznego Pull. Sprawdzone: sukces w 2 min 8 s.
  Git folder w workspace służy już tylko do pracy interaktywnej.
- [x] Pierwsze uruchomienie z harmonogramu: 2026-11-18 06:00, sukces w 2 min 37 s.
- [x] Power BI na danych z Databricks (2026-11-18): skrypt `scripts/set_powerbi_source.py` przełączył 11 tabel
  na `pl_cities.gold.*` przez SQL Warehouse (konektor „Databricks”, `DatabricksMultiCloud.Catalogs`;
  parametry `DatabricksHost`, `DatabricksHttpPath` w `expressions.tmdl`; tryb Import). Odświeżone w Power BI
  Desktop, opublikowane do Fabric (`pl-cities-lakehouse`), poświadczenia Databricks w ustawieniach modelu,
  odświeżanie codziennie 07:00 (po jobie o 06:00); pierwsze odświeżenie w chmurze 2026-11-18 13:27.
  Token Databricks dla Power BI wygasa po 90 dniach (ok. 2027-02-16): wtedy nowy token w Desktop i Fabric.
- [x] README przepisane pod chmurę (2026-11-18): diagram architektury, DAG joba, tabela decyzji, koszty (0 zł),
  rewizja danych Open-Meteo, instrukcja dla Databricks; zrzuty raportu, joba i lineage w `docs/images/`.
- [x] Tydzień 8: porównanie Databricks i Fabric: [databricks-vs-fabric.md](databricks-vs-fabric.md).
  Wersja próbna Fabric włączona ręcznie 2026-11-18 (60 dni, region Poland Central). Lakehouse `pl_cities`
  ze schematami, wheel w `Files/libs`, notebook `fabric/pl_cities_fabric.ipynb`: 1. uruchomienie 4 min 26 s,
  przyrostowe 1 min 37 s; ranking 2025 jak lokalnie (historia pogody wgrana z laptopa, bo pobieranie
  z Fabric trafiło na 429). Bez harmonogramu w Fabric (dublowałby Databricks).

## Główny plan: zakończony (2026-11-18)

Pipeline działa codziennie w chmurze (Databricks 06:00 → Fabric 07:00), README ze zrzutami, porównanie platform.
Opcjonalne dalsze kroki: Asset Bundles (job jako kod w `infra/`), poprawki Power BI (lista wyżej),
wyjaśnienie różnicy 0,0002 w affordability, Azure pay-as-you-go z ADLS.
- [ ] Opcjonalnie: Azure pay-as-you-go (ADLS Gen2, Azure Databricks) na krótko, z budżetem.
