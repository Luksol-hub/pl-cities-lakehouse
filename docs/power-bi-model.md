# Model gwiazdy dla Power BI

Pliki: `data/gold/*.parquet`, tworzone przez:

```powershell
python -m pl_cities_lakehouse.export_gold
```

Lokalnie to zastępstwo tabel Delta (Spark na Windowsie nie zapisuje plików bez winutils).
Na Databricks te same tabele, z tymi samymi nazwami i kolumnami, będą tabelami Delta;
w Power BI zmienia się wtedy tylko źródło danych, model i miary zostają.

## Tabele

| Tabela | Rodzaj | Ziarno | Klucze |
| --- | --- | --- | --- |
| `dim_date` | wymiar | dzień (2006-07-01 – 2026-06-30) | `date_key` (rrrrmmdd) |
| `dim_location` | wymiar, SCD1 | miejscowość (34: 17 w rankingu + miasta stadionów) | `location_key` |
| `dim_team` | wymiar, SCD2 | drużyna i okres z jednym miastem stadionu | `team_key` |
| `dim_market_option` | tabela rozłączona (bez relacji) | opcja fragmentatora: Wtórny, Pierwotny, Średnia z obu | `option` |
| `fact_weather_daily` | fakt | miejscowość, dzień | `location_key`, `date_key` |
| `fact_housing_price` | fakt | rynek, typ ceny, miasto, kwartał | `location_key`, `date_key` (1. dzień kwartału) |
| `fact_wage` | fakt | miasto, rok | `location_key`, `date_key` (1 stycznia) |
| `fact_air_quality` | fakt | miasto, rok | `location_key`, `date_key` (1 stycznia) |
| `fact_match` | fakt | mecz | `date_key`, `location_key`, `home_team_key`, `away_team_key` |
| `mart_city_score` | gotowy wynik | rynek, miasto, rok | `location_key`, `date_key` + czytelne `city`, `year` |
| `mart_match_weather` | gotowy wynik | czynnik pogody, przedział | brak (tabela samodzielna) |

## Relacje (jeden do wielu, wymiar → fakt)

- `dim_date[date_key]` → `date_key` w każdej tabeli faktów i w `mart_city_score`
- `dim_location[location_key]` → `location_key` w każdej tabeli faktów i w `mart_city_score`
- `dim_team[team_key]` → `fact_match[home_team_key]` (aktywna)
- `dim_team[team_key]` → `fact_match[away_team_key]` (**nieaktywna**; w mierze użyj `USERELATIONSHIP`)

Kierunek filtrowania: pojedynczy, od wymiaru do faktu. `dim_team` pełni dwie role (gospodarz i gość),
to tzw. **role-playing dimension**; alternatywnie można wczytać `dim_team` drugi raz jako „Away Team”.

## Miary DAX (25)

Generowane przez `scripts/build_pbir.py`; liczone na żywo, więc reagują na suwak roku i przyciski rynku.

- **`mart_city_score`:** `Warunki życia`, `m² za pensję`, `Cena za m²`, `Pensja brutto`; na żywo:
  `Ocena dostępności` (min-max wśród wybranych miast, `ALLSELECTED`), `Wynik końcowy` (50/50), `Miejsce` (`RANKX`);
  tekstowe na karty: najlepsze miasto, najlepsze warunki, najwięcej i najmniej m² za pensję.
  `m² za pensję` i `Cena za m²` czytają wybraną opcję rynku (`SELECTEDVALUE(dim_market_option[option])`)
  i filtrują `market` przez `SWITCH` + `CALCULATE`; „Średnia z obu” uśrednia oba rynki.
- **`dim_location`:** `Miasto`, `Województwo` (`SELECTEDVALUE`, do kart tooltipa).
- **`fact_weather_daily`:** `Dni z deszczem`, `Dni z mrozem`, `Dni upalne`. **`fact_air_quality`:** `Dni smogu`.
- **`fact_match`:** `Mecze`, `Gole na mecz`, odsetki wygranych gospodarzy, remisów i wygranych gości.
- **`mart_match_weather`:** mecze, gole i odsetek wygranych gospodarzy w przedziale pogody.

## Strony raportu

- **Pytanie A (1280×720):** suwak roku, przyciski rynku, 4 karty KPI, wykres punktowy z tooltipem, tabela rankingu,
  dwa wykresy obszarowe 2007–2025. Interakcje: suwak nie filtruje wykresów w czasie; klik w tabeli lub na wykresie
  punktowym pokazuje przebieg miasta w czasie, nie zmienia kart; klik na wykresie w czasie niczego nie filtruje.
- **Pytanie B (1280×720):** 4 karty, trzy wykresy słupkowe (deszcz, temperatura, wiatr) z filtrem na czynnik, wniosek.
- **Tooltip: miasto (ukryta):** nazwa, województwo i 8 kafelków KPI.
- **Motyw:** `StaticResources/RegisteredResources/pl-cities-theme.json` (jasne tło, białe zaokrąglone karty z cieniem,
  niebieska paleta, styl fragmentatora przycisków).

## Wskazówki

- Fakty roczne i kwartalne wskazują pierwszy dzień okresu w `dim_date`; filtruj je po `year` lub `quarter`,
  nie po pojedynczych dniach.
- Ceny z dwóch rynków uśredniaj (`AVERAGE`), nie sumuj.
- `dim_location[is_ranked]` = prawda dla 17 miast z rankingu; miasta stadionów służą tylko modułowi B.
- Nowa tabela dodana przez pliki jest pusta do odświeżenia w Power BI Desktop: odśwież przed publikacją.
- Publikacja: obszar roboczy Fabric `pl-cities-lakehouse`, model `pl-cities-report`.
