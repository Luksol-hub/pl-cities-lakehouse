# Tydzień 1: przygotowanie lokalne (bez Azure)

Konto Azure zakładamy dopiero, gdy lokalne parsery działają, bo kredyt startowy jest ważny tylko 30 dni od założenia konta.

- [x] Git, Python 3.12 i Java 17 zainstalowane
- [x] Repo utworzone i sklonowane
- [ ] Szkielet projektu zacommitowany (pull request z CI)
- [ ] `python -m venv .venv`, `pip install -e ".[dev]"`, `pytest` przechodzi
- [ ] Topics dodane na GitHubie
- [ ] Próbki danych pobrane: Open-Meteo, NBP, GUS BDL, football-data.co.uk
- [ ] Lista miast ustalona na podstawie zakresu danych NBP
- [ ] Wskaźnik warunków życia zdefiniowany (składniki, normalizacja, wagi)
- [ ] Pierwszy parser (pogoda) działa lokalnie w PySpark i zapisuje do Delta lub Parquet
