# Tydzień 1: przygotowanie lokalne (bez Azure)

Konto Azure zakładamy dopiero, gdy lokalne parsery działają, bo kredyt startowy jest ważny tylko 30 dni od założenia konta.

- [x] Git, Python 3.12 i Java 17 zainstalowane
- [x] Repo utworzone i sklonowane
- [x] Szkielet projektu zacommitowany (pull request z CI)
- [x] `python -m venv .venv`, `pip install -e ".[dev]"`, `pytest` przechodzi
- [ ] Topics dodane na GitHubie
- [ ] Próbki danych pobrane: Open-Meteo, NBP, GUS BDL, football-data.co.uk
  - [x] NBP (ceny mieszkań, BaRN)
  - [ ] Open-Meteo
  - [ ] GUS BDL
  - [ ] football-data.co.uk
- [x] Lista miast ustalona na podstawie zakresu danych NBP
- [ ] Wskaźnik warunków życia zdefiniowany (składniki, normalizacja, wagi)
- [ ] Pierwszy parser działa lokalnie w PySpark i zapisuje do Delta lub Parquet
  - [x] Parser NBP czyta i parsuje dane lokalnie (zapis do Parquet przetestujemy na Databricks, bo Spark na Windowsie wymaga winutils)

## Lista miast (17)

Białystok, Bydgoszcz, Gdańsk, Gdynia, Katowice, Kielce, Kraków, Lublin, Łódź, Olsztyn, Opole, Poznań, Rzeszów, Szczecin, Warszawa, Wrocław, Zielona Góra.

Źródło: NBP, Baza cen nieruchomości mieszkaniowych (16 miast wojewódzkich i Gdynia).