# Tydzień 1: przygotowanie lokalne (bez Azure)

Start projektu: 2026-10-22.

Konto Azure zakładamy dopiero, gdy lokalne parsery działają, bo kredyt startowy jest ważny tylko 30 dni od założenia konta.

- [x] Git, Python 3.12 i Java 17 zainstalowane
- [x] Repo utworzone i sklonowane
- [x] Szkielet projektu zacommitowany (pull request z CI)
- [x] `python -m venv .venv`, `pip install -e ".[dev]"`, `pytest` przechodzi
- [ ] Topics dodane na GitHubie
- [ ] Próbki danych pobrane: Open-Meteo, NBP, GUS BDL, football-data.co.uk
  - [x] NBP (ceny mieszkań, BaRN)
  - [x] Open-Meteo (pogoda dzienna 2006-07-01 – 2026-06-30, 17 miast)
  - [ ] GUS BDL
  - [ ] football-data.co.uk
- [x] Lista miast ustalona na podstawie zakresu danych NBP
- [ ] Wskaźnik warunków życia zdefiniowany (składniki, normalizacja, wagi)
- [ ] Pierwszy parser działa lokalnie w PySpark i zapisuje do Delta lub Parquet
  - [x] Parser NBP czyta i parsuje dane lokalnie (zapis do Parquet przetestujemy na Databricks, bo Spark na Windowsie wymaga winutils)
  - [x] Pogoda Open-Meteo: pobieranie z retry i obsługą limitów, surowe JSON-y w `data/raw/open_meteo/`, tabela Sparka (124 185 wierszy)

## Lista miast (17)

Białystok, Bydgoszcz, Gdańsk, Gdynia, Katowice, Kielce, Kraków, Lublin, Łódź, Olsztyn, Opole, Poznań, Rzeszów, Szczecin, Warszawa, Wrocław, Zielona Góra.

Źródło: NBP, Baza cen nieruchomości mieszkaniowych (16 miast wojewódzkich i Gdynia).