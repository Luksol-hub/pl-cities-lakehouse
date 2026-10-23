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

## Wskazówki

- Fakty roczne i kwartalne wskazują pierwszy dzień okresu w `dim_date`; filtruj je po `year` lub `quarter`,
  nie po pojedynczych dniach.
- Ceny z dwóch rynków uśredniaj (`AVERAGE`), nie sumuj.
- `dim_location[is_ranked]` = prawda dla 17 miast z rankingu; miasta stadionów służą tylko modułowi B.
- `mart_city_score` zawiera już oceny i miejsca w rankingu; liczenie ich od nowa w DAX nie jest potrzebne.
