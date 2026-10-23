# Notatki pod rekrutację

Pojęcia, które pojawiły się w projekcie: co znaczą, gdzie są w kodzie i jak o nich mówić na rozmowie.
Plik rośnie razem z projektem.

## Architektura danych

### Architektura medalionowa (bronze, silver, gold)

Dane układa się w trzech warstwach, coraz czystszych i bliższych pytaniu biznesowemu.

- **Bronze:** dane wierne źródłu plus metryczka. Kopia zapasowa prawdy.
- **Silver:** dane oczyszczone i spójne: bez duplikatów, z ujednoliconymi nazwami, sprawdzone testami.
- **Gold:** tabele pod konkretne pytania i raporty (u nas model gwiazdy i ranking miast).

**W projekcie:** parser NBP i pobieranie pogody to bronze; silver w tygodniu 4, gold w tygodniu 5.

**Na rozmowie:** „Bronze przechowuje, silver porządkuje, gold odpowiada. Gdy zrobię błąd w logice,
przeliczam od bronze, bez ponownego pobierania ze źródła.”

### Gdzie trzymać logikę biznesową

Bronze zostaje wierny źródłu; decyzje, które mogą się zmienić (progi, sposób łączenia), idą do silver.
Zmiana decyzji to wtedy poprawka jednej funkcji i przeliczenie, bez ponownego parsowania źródła.

**W projekcie:** GIOŚ w bronze ma wiersz na stację i rok; odrzucenie stacji z kompletnością < 75%
i mediana ze stacji w mieście dzieją się w silver.

### Ziarno tabeli (grain) i klucz

Ziarno to odpowiedź na pytanie „co oznacza jeden wiersz”. Klucz to zestaw kolumn, który jednoznacznie
wskazuje wiersz. Jeśli klucz się powtarza, ziarno jest źle zrozumiane i agregacje policzą coś podwójnie.

**W projekcie:** w GIOŚ wiersz to stacja, rok i **metoda pomiaru** (`24g` manualna, `1g` automatyczna).
Bez metody w kluczu 1127 par stacja-rok miało po dwa wiersze, a mediana liczyłaby te stacje podwójnie.

### Landing zone / raw

Zapis danych ze źródła dokładnie tak, jak przyszły (plik Excel, odpowiedź JSON), zanim cokolwiek się z nimi zrobi.

**W projekcie:** `data/raw/nbp/ceny_mieszkan.xlsx`, `data/raw/open_meteo/*.json`.

**Na rozmowie:** „Trzymam surowe odpowiedzi, żeby móc ponownie sparsować dane bez odpytywania API,
nie zużywać limitów i mieć dowód, co źródło zwróciło.”

### Powielanie danych między warstwami

Kopie w kilku warstwach to świadoma decyzja: źródła się zmieniają i znikają, każda warstwa ma inną rolę,
formaty kolumnowe (Parquet, Delta) czyta się szybciej niż Excel, a miejsce w chmurze jest tanie.

### ADLS Gen2 (Azure Data Lake Storage)

Magazyn plików w Azure przystosowany do analityki: prawdziwe foldery (opcja „hierarchical namespace”),
uprawnienia do folderów, równoległy odczyt przez Sparka. Zakłada się go jako konto magazynu
(storage account) z kontenerami, np. `raw`, `bronze`, `silver`, `gold`. Płaci się za ilość danych i operacje.

**W projekcie:** docelowe miejsce na surowe pliki (dziś `data/raw/`) i tabele Delta wszystkich warstw;
czyta z niego Databricks, a tabele gold także Power BI i Fabric.

### Rozdzielenie magazynu i obliczeń (separation of storage and compute)

Dane leżą w tanim magazynie (ADLS), a obliczenia robi osobny klaster (Databricks), który płaci się za czas działania.
Klaster wyłączasz po pracy, dane zostają; możesz też włączyć kilka klastrów na tych samych danych.

**Na rozmowie:** „Databricks liczy, ADLS przechowuje. Klaster ma auto-wyłączanie, więc nie płacę za bezczynność,
a dane w ADLS są niezależne od tego, czy klaster działa.”

### Model gwiazdy (star schema)

Tabele **faktów** (liczby, np. ceny, pogoda) otoczone tabelami **wymiarów** (kto, gdzie, kiedy: data, miasto).
Wspólne wymiary pozwalają łączyć różne fakty, np. ceny mieszkań z pogodą po mieście i dacie.

### Wskaźnik złożony, normalizacja min-max i wagi

Wskaźnik złożony łączy kilka miar w jedną liczbę. Miary mają różne skale (dni deszczu, dni mrozu),
więc najpierw normalizuje się je do 0–1: **min-max** `(wartość - min) / (max - min)`,
a gdy mniej znaczy lepiej, odwrotnie: `(max - wartość) / (max - min)`. Potem średnia ważona.

**W projekcie:** wskaźnik warunków życia, definicja w `docs/quality-of-life-index.md`.

**Na rozmowie:** „Wagi są subiektywne i opisałem je otwarcie. Odrzuciłem wiatr, bo nie różnicował miast,
i średnią temperaturę zimą, bo dublowała dni z mrozem.”

### Dostępność mieszkań (housing affordability)

Cena za m² sama w sobie myli, bo zarobki w miastach są różne. Dzielimy pensję przez cenę za m²:
wynik to liczba m² za jedną pensję.

**Na rozmowie:** „Zarobków nie wrzuciłem do wskaźnika warunków życia, bo mierzą co innego.
Użyłem ich do urealnienia cen.”

## Jakość i niezawodność

### Idempotentność

Uruchomienie procesu raz czy wiele razy daje ten sam wynik, bez dublowania danych.

**W projekcie:** pobieranie pogody pomija miasta, które już mają plik; parser NBP nadpisuje
tabelę bronze w całości (`mode("overwrite")`), bo NBP publikuje pełną historię w każdym pliku.

**Na rozmowie:** „Pipeline mogę bezpiecznie uruchomić ponownie po awarii, bo nie zdubluje danych.”

### Fail fast

Zgłoś błąd jak najwcześniej, tam gdzie powstał, z czytelnym powodem, zamiast iść dalej ze złymi danymi.

**W projekcie:** `raise_for_status()` przy zapytaniach do API; parser NBP zatrzymuje się,
gdy lista miast się nie zgadza; `zip(..., strict=True)` przy listach różnej długości.

**Na rozmowie:** „Wolę, żeby pipeline się zatrzymał z jasnym błędem, niż po cichu załadował niepełne dane.”

### Kontrole jakości danych (data quality checks)

Testy jednostkowe sprawdzają **kod** na sztucznych danych; kontrole jakości sprawdzają **prawdziwe dane**
przy każdym uruchomieniu pipeline'u. Typowe reguły: unikalny klucz, brak pustych wartości,
wartości w sensownym zakresie, brak dziur w datach. Złamana reguła zatrzymuje pipeline z listą problemów,
więc złe dane nie dochodzą do gold i raportu.

**W projekcie:** `common/quality.py` (`assert_quality`, `missing_days`), użyte w `silver_weather`.
Na Databricks podobne reguły można zapisać jako *expectations* w Delta Live Tables
albo użyć bibliotek typu Great Expectations.

**Na rozmowie:** „Każda tabela silver ma kontrole: klucz, puste wartości, zakresy i ciągłość dat.
Pipeline zatrzymuje się z listą wszystkich problemów naraz, a nie na pierwszym.”

### Dopasowanie nazw między źródłami

Każde źródło nazywa te same rzeczy inaczej: NBP „Kraków”, GUS „Powiat m. Kraków”,
a Warszawę „Powiat m. st. Warszawa”. Mapowanie trzeba zapisać jawnie w kodzie
i sprawdzić, że wszystkie miasta się znalazły.

**W projekcie:** `gus_unit_name` w `ingestion/gus_bdl.py`; brak miasta zatrzymuje ładowanie z listą brakujących.
W danych piłkarskich ta sama drużyna ma dwie nazwy („Gornik Z.” i „Gornik Zabrze”), a podobne nazwy
to różne kluby („Zaglebie” to Lubin, „Zaglebie Sosnowiec” to Sosnowiec); mapowanie jest w `common/teams.py`,
a kontrola sprawdza, że każda drużyna z danych ma miasto.
Przy wyszukiwaniu współrzędnych (geocoding) nazwy też bywają niejednoznaczne: w Polsce jest kilka
miejscowości o nazwie Radom czy Chorzów, więc wynik sprawdzamy po województwie.

### Kody jakości wartości

Źródła statystyczne oznaczają wartości specjalne kodem obok liczby. W GUS BDL `attrId = 1` to zwykła wartość,
a np. `91` to brak danych zapisany jako `0.0`. Bez filtra zero trafiłoby do średnich jak prawdziwa pensja.

**W projekcie:** `to_records` w `ingestion/gus_bdl.py` bierze tylko `attrId == 1`.

### Walidacja schematu

Sprawdzenie, czy dane mają oczekiwany układ (kolumny, typy, wartości), zanim trafią dalej.

**W projekcie:** `EXPECTED_CITIES` w parserze NBP; `SCHEMA` z typami kolumn dla Sparka.

### Data lineage i kolumny audytowe

Możliwość prześledzenia, skąd pochodzi każdy wiersz. Kolumny audytowe to metryczka dopisywana przy ładowaniu.

**W projekcie:** `source_file` i `ingested_at` w tabeli NBP.

## Praca z API

### Rate limit i błąd 429 Too Many Requests

Darmowe API ograniczają liczbę zapytań w czasie. Open-Meteo: 600 na minutę, 5000 na godzinę, 10 000 na dzień;
zapytanie o długi okres, wiele zmiennych lub wiele lokalizacji liczy się jak kilka zapytań.

**W projekcie:** po błędzie 429 program czeka 60 sekund i próbuje ponownie.

### Retry i exponential backoff

Ponawianie zapytania po chwilowym błędzie (timeout, pusta odpowiedź), z coraz dłuższą przerwą: 2 s, 4 s, 8 s…

**W projekcie:** `fetch_daily_weather` w `ingestion/open_meteo.py`, do 3 prób.

**Na rozmowie:** „Jak radzę sobie z zawodnym API? Retry z backoffem, obsługa 429,
idempotentne pobieranie i zapis surowych odpowiedzi.”

### Paginacja

Dzielenie dużej odpowiedzi API na strony pobierane kolejnymi zapytaniami.
Zmniejsza rozmiar jednej odpowiedzi, ale **nie omija limitów**: stron jest więcej, a zapytań tyle samo
albo więcej. Open-Meteo nie ma paginacji, bo cały okres dla miasta mieści się w jednej odpowiedzi.

## Analiza wyników

### Mała próba i wielokrotne porównania

Średnia z 2 meczów nic nie znaczy, a z 258 jest niepewna. Im mniejsza grupa, tym większe przypadkowe wahania.
Gdy porównujesz wiele grup naraz (u nas 9 przedziałów pogody), któraś prawie na pewno wyjdzie „ciekawa”
czysto przez przypadek. Dlatego w tabeli zawsze jest liczba obserwacji, a pojedyncze odchylenie to trop, nie dowód.

**W projekcie:** `gold_match_weather` ma kolumnę `matches`; wnioski w `docs/module-b-weather-football.md`.

### Korelacja a przyczynowość

Korelacja mierzy, czy dwie wielkości zmieniają się razem (od −1 do 1, 0 = brak związku liniowego).
Nawet wysoka korelacja nie dowodzi przyczyny: zimą mniej goli może wynikać z gorszej murawy, nie z temperatury.

**Na rozmowie:** „Moduł B dał wynik w praktyce negatywny: korelacje bliskie zera. Opisałem go uczciwie,
z liczbą meczów w każdej grupie i zastrzeżeniem, że to związek, a nie przyczyna.”

## Testy

### Testy jednostkowe (pytest)

Małe testy sprawdzające pojedyncze funkcje na sztucznych danych. Szybkie, bez internetu i bez chmury,
więc CI może je uruchamiać przy każdej zmianie.

**W projekcie:** `tests/test_nbp_housing.py` (sztuczny Excel), `tests/test_open_meteo.py` (sztuczna odpowiedź API).

### Mock / monkeypatch

Podmiana prawdziwej zależności (np. zapytania do API albo czekania `sleep`) na udawaną wersję na czas testu.
Dzięki temu da się sprawdzić zachowanie przy błędach serwera bez czekania i bez prawdziwego serwera.

**W projekcie:** `FakeResponse` udaje odpowiedź API; testy sprawdzają retry po błędzie 500,
poddanie się po 3 próbach z błędem 429 i pomijanie już pobranych miast.

**Na rozmowie:** „Logikę retry przetestowałem, podmieniając klienta HTTP na atrapę zwracającą błędy.
Test nie zależy od internetu i trwa ułamek sekundy.”

### Fixture

Przygotowanie wspólne dla wielu testów, np. jedna sesja Sparka na cały przebieg (`tests/conftest.py`)
albo tymczasowy folder `tmp_path`, który pytest sam tworzy i sprząta.

## Formaty danych

### Format szeroki a długi

- **Szeroki:** wartości rozłożone po kolumnach (Excel NBP: miasta w kolumnach). Wygodny dla człowieka.
- **Długi:** jeden wiersz = jedna obserwacja (wynik parsera NBP). Wygodny do filtrowania i łączenia.

**Kiedy który:** długi, gdy wartości są tej samej miary (cena ofertowa i transakcyjna w zł/m²);
osobne kolumny, gdy miary mają różne jednostki (temperatura °C, opady mm, wiatr km/h).

### JSON i format kolumnowy

Odpowiedź Open-Meteo trzyma każdy pomiar jako osobną listę; elementy z tej samej pozycji należą do jednego dnia.
Funkcja `to_records` „zszywa” listy w wiersze za pomocą `zip`.

### Parquet i Delta

**Parquet:** kolumnowy format plików, szybki do analiz i dobrze kompresowany.
**Delta:** Parquet plus dziennik transakcji: zapisy atomowe, MERGE, historia wersji (**time travel**).

## Spark

### Spark i PySpark

Spark to silnik napisany w Scali, działający na Javie (dlatego potrzebna Java 17).
PySpark to interfejs w Pythonie: piszesz w Pythonie, liczy silnik w Javie.

### PySpark a Excel: ściąga

| W Excelu | W PySparku | Gdzie w projekcie |
| --- | --- | --- |
| tabela | DataFrame | każda tabela bronze i silver |
| filtr | `filter` | stacje z kompletnością ≥ 75% (`silver_pm10`) |
| sortowanie i „weź pierwszy” | `Window` + `row_number` | metoda 24g przed 1g (`silver_pm10`) |
| tabela przestawna | `groupBy` + `agg` | mediana dni smogu na miasto i rok (`silver_pm10`) |
| kolumna z formułą | `withColumn` | metryczka `ingested_at` (`to_dataframe`) |
| WYSZUKAJ.PIONOWO | `join` | łączenie źródeł w silver i gold |

### Gdzie w projekcie jest zwykły Python, a gdzie Spark

Pobieranie (`requests`) i rozbiór plików (Excel, JSON, CSV) to zwykły Python: pliki są małe, mają nieregularny
układ, a Spark nie czyta Excela. Dane wchodzą do Sparka w `to_dataframe` (bronze), a przekształcenia
(`filter`, `Window`, `groupBy`) dzieją się w Sparku (silver i gold).

**Gdyby danych było za dużo na jeden komputer:** pobieranie z API dalej robi zwykły Python (Spark nie wysyła
zapytań HTTP), ale surowe pliki trafiają od razu do chmury, a rozbiór robi Spark na klastrze:
`spark.read.json` / `spark.read.csv` czytają te formaty natywnie, a listy z odpowiedzi Open-Meteo
dałoby się „zszyć” w Sparku funkcjami `arrays_zip` i `explode` zamiast pętli `zip` w Pythonie.
Na Databricks nowe pliki w chmurze może automatycznie wczytywać **Auto Loader**.

### Funkcje okna (window functions)

`groupBy` zwija wiersze do jednego na grupę. Funkcja okna liczy wartość dla grupy („okna”),
ale **zostawia każdy wiersz** i dokleja mu wynik. Okno definiuje `Window.partitionBy(...)`,
opcjonalnie z `orderBy(...)`.

**W projekcie:**
- `silver_pm10`: `row_number()` w oknie stacja + rok wybiera metodę 24g przed 1g (deduplikacja z priorytetem),
- `gold_quality_of_life`: `min()` i `max()` w oknie rok dają każdemu miastu zakres z jego roku
  do normalizacji min-max, bez dodatkowego `groupBy` i `join`.

- `gold_city_score`: `rank()` w oknie rok + rynek, posortowanym malejąco po wyniku, daje miejsca w rankingu.

`rank()` a `row_number()`: przy remisie `rank()` daje obu miastom to samo miejsce (1, 2, 2, 4),
a `row_number()` zawsze inne numery (1, 2, 3, 4), więc remis rozstrzyga przypadkowo.
Do rankingu `rank()`, do deduplikacji `row_number()`.

Inne typowe zastosowania: porównanie z poprzednim okresem (`lag`), sumy narastające.

**Na rozmowie:** „`groupBy` zwija, okno nie zwija. Okna użyłem do deduplikacji z priorytetem
i do normalizacji w obrębie roku.”

### Join i jego rodzaje

`join` łączy dwie tabele po wspólnych kolumnach, jak WYSZUKAJ.PIONOWO w Excelu.
- **inner:** zostają tylko wiersze, które znalazły parę w obu tabelach; reszta znika po cichu.
- **left:** zostają wszystkie wiersze z lewej tabeli; brak pary daje puste kolumny z prawej.

**W projekcie:** `silver_matches` łączy mecze z pogodą po mieście i dacie (`left`), a potem sprawdza,
czy któryś mecz nie dostał pogody. Przy `inner` taki mecz zniknąłby bez śladu.

**Na rozmowie:** „Wybrałem left join z kontrolą pustych wartości, bo inner join gubi niedopasowane
wiersze bez ostrzeżenia. Wolę wiedzieć, że czegoś brakuje.”

**Join po przedziale (range join):** warunek łączenia to nie tylko równość kluczy, ale też „data mieści się
w okresie”: `home_team == team AND match_date BETWEEN valid_from AND valid_to`. Tak łączy się fakty
z wymiarem SCD2. W projekcie: `apply_relocations` w `silver_matches` przypisuje mecz do miasta,
w którym klub grał w tym okresie (168 meczów).

Inner join bywa jednak świadomym wyborem: w `gold_quality_of_life` miasto bez danych PM10 w danym roku
ma wypaść z rankingu, więc inner join z komentarzem w kodzie robi dokładnie to, co trzeba.

### Leniwe wykonanie (lazy evaluation)

Polecenia Sparka (`filter`, `groupBy`, `withColumn`) niczego od razu nie liczą, tylko budują plan.
Obliczenia ruszają dopiero przy akcji, która potrzebuje wyniku: `show()`, `count()`, `collect()`, zapis.
Dzięki temu Spark może zoptymalizować cały plan naraz, np. przefiltrować dane przed grupowaniem.

**Konsekwencja:** każda akcja to osobne zadanie i osobne przejście przez dane. Siedem `count()` na tej samej
tabeli to siedem odczytów. W `assert_quality` puste wartości i zakresy liczymy jednym `agg` z `count_if`
dla każdej reguły, czyli w jednym przejściu; testy przyspieszyły z ok. 2:15 do ok. 1:00.

### Delta a Spark

Delta to format przechowywania tabeli: pliki Parquet z danymi plus folder `_delta_log` z dziennikiem wersji.
Spark to program, który ten format obsługuje. Przy zapisie tworzy nowe pliki Parquet i dopisuje do dziennika
„wersja N = te pliki”; przy odczycie najpierw czyta dziennik, żeby wiedzieć, które pliki są aktualne.
Stare pliki zostają, stąd **time travel**. Jeśli zapis padnie w połowie, wpis w dzienniku się nie pojawia
i tabela zostaje w poprzedniej wersji (zapis atomowy). Deltę czytają też Power BI i Microsoft Fabric.

### Kiedy Spark nie jest potrzebny

Przy dziesiątkach tysięcy wierszy wystarczy zwykły Python lub pandas. Spark ma sens przy milionach wierszy
i obliczeniach na wielu maszynach.

**Na rozmowie:** „Przy tej skali Spark nie był konieczny. Użyłem go, bo docelowa platforma to Databricks
i Delta, a rozwiązanie skaluje się bez zmian.”

### DataFrame, schemat, partycjonowanie

- **DataFrame:** tabela Sparka.
- **Schemat:** nazwy i typy kolumn, podane jawnie (`SCHEMA`), zamiast zgadywania przez Sparka.
- **Nullable:** czy kolumna może być pusta. Klucze (`city`, `date`) nie mogą, pomiary mogą,
  bo źródło czasem nie ma wartości dla danego dnia. Pusty pomiar to „brak danych”, a nie zero.
- **partitionBy:** zapis danych w podfolderach według kolumny (np. `market=primary/`),
  żeby zapytania z filtrem czytały tylko potrzebną część.

### Spark na Windowsie

Zapis plików przez Sparka na Windowsie wymaga `winutils.exe`. CI i Databricks działają na Linuksie,
więc problem dotyczy tylko lokalnego komputera.

## Git i CI

- **Branch (gałąź):** osobna linia zmian; pracujemy na gałęzi, nie bezpośrednio na `main`.
- **Commit:** zapisana wersja zmian z opisem.
- **Pull request (PR):** prośba o scalenie gałęzi do `main`, z podglądem zmian i wynikiem testów.
- **Fast-forward:** scalenie bez konfliktów, gdy wystarczy „przewinąć” gałąź do przodu.
- **CI (Continuous Integration):** automatyczne sprawdzenie kodu przy każdym PR i pushu do `main`
  (u nas `ruff` i `pytest` na Linuksie, plik `.github/workflows/ci.yml`).
- **Lint:** sprawdzanie kodu bez uruchamiania go (nieużywane importy, długie linie, błędy); u nas `ruff`.
- **Zasada:** nie scalaj PR, zanim CI nie pokaże zielonego wyniku.
