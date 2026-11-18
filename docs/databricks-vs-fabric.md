# Databricks a Microsoft Fabric

Stan na 2026-11-18. Ten sam pipeline (bronze, silver, gold), ta sama paczka `pl_cities_lakehouse`,
dwie platformy. Na Databricks działa codzienny job; w Fabric ten sam pipeline uruchomiłem z jednego notebooka
([fabric/pl_cities_fabric.ipynb](../fabric/pl_cities_fabric.ipynb)) na wersji próbnej Fabric.

## Co sprawdziłem

| Element | Databricks (Free Edition) | Fabric (wersja próbna, region Poland Central) |
| --- | --- | --- |
| Ingestion, Delta, MERGE, silver, gold | ✅ codziennie o 6:00 | ✅ dwa ręczne uruchomienia |
| Orkiestracja | ✅ job z DAG, alerty, kod z Gita | ❌ nie ustawiałem (opis niżej) |
| Model Power BI, odświeżanie, raport | – | ✅ model czyta gold z Databricks, odświeżanie o 7:00 |
| Direct Lake (Power BI prosto z OneLake) | – | ❌ niesprawdzone |

## Pomiary

Czasy etapów w Fabric mierzy notebook (`step()`); w Databricks to czasy zadań joba.

| Etap | Databricks: job (zakres z 4 uruchomień) | Fabric: 1. uruchomienie | Fabric: 2. uruchomienie |
| --- | --- | --- | --- |
| bronze pogody (lookback 7 dni + MERGE) | 50–150 s | 161 s (z utworzeniem tabeli z historią) | 15 s |
| bronze snapshotów | 56–167 s | 21 s | 17 s |
| silver + gold | 62–71 s | 84 s | 65 s |
| **całość** | **2 min 8 s – 3 min 51 s** | **4 min 26 s** | **1 min 37 s** |

**Jak to czytać (to nie jest uczciwy wyścig):**
- Fabric liczył w **jednej, już rozgrzanej sesji** notebooka; czas startu sesji nie jest wliczony.
  Job Databricks uruchamia każde zadanie od zera (start obliczeń serverless w każdym zadaniu).
- W Databricks zadania bronze idą równolegle, w notebooku Fabric po kolei.
- Pobieranie z API zależy od sieci i limitów źródła, nie od platformy.
- Wniosek: obie platformy liczą ten pipeline w 1,5–4 minuty; przy tej skali danych różnice wynikają
  z narzutu startu i sposobu uruchomienia, a nie z wydajności Sparka.

**Wyniki zgodne:** ranking 2025 w Fabric jest identyczny z lokalnym (Szczecin 0,64 na rynku wtórnym,
Zielona Góra 0,80 na pierwotnym). Databricks pokazuje 0,63, bo pobrał historię pogody po rewizji
Open-Meteo, a do Fabric wgrałem pliki z laptopa sprzed rewizji. Ten sam kod + te same dane = ten sam wynik.

## Co poszło inaczej niż w Databricks (lekcje)

1. **Wersja próbna Fabric:** najpierw „nie jest dostępna dla Twojego konta”; ręczne włączenie z okna
   „Aktywowanie 60-dniowej bezpłatnej wersji próbnej” zadziałało. Lakehouse i Spark wymagają pojemności Fabric;
   sama wersja próbna Power BI nie wystarcza.
2. **Lakehouse musi być podpięty do notebooka** (domyślny), inaczej nie ma ścieżki `/lakehouse/default/Files`.
3. **Limit API (429):** pobieranie 20 lat historii z Fabric skończyło się „Too Many Requests”. Ruch wychodzi
   ze współdzielonych adresów IP chmury, więc limit darmowego API mógł zużyć ktoś inny. Historię wgrałem z plików.
4. **Cache podmontowanego magazynu:** po podmianie plików w trakcie sesji notebook czytał je ucięte
   (zapamiętany stary rozmiar). Pomogło zatrzymanie sesji. Wniosek: pliki surowe są niezmienne, nie nadpisuję ich.
5. **Python 3.13** w Fabric (lokalnie 3.12): paczka działała bez zmian.

## Porównanie

| Obszar | Databricks | Fabric |
| --- | --- | --- |
| Model | platforma danych na chmurze dostawcy (Azure, AWS, GCP) | usługa SaaS Microsoftu, wszystko w jednym obszarze roboczym |
| Magazyn | tabele Delta w magazynie chmury (u mnie zarządzany przez Databricks, w firmie ADLS / S3) | OneLake: jeden magazyn dla organizacji, tabele Delta w lakehouse; **skróty** (shortcuts) do ADLS / S3 bez kopiowania |
| Katalog i uprawnienia | Unity Catalog: `katalog.schemat.tabela`, uprawnienia, lineage zapisywany automatycznie | obszary robocze i role, lakehouse ze schematami; zarządzanie przez Microsoft Purview |
| Pliki surowe | wolumin Unity Catalog (`/Volumes/...`) | **Files** w lakehouse (`/lakehouse/default/Files/...`) |
| Obliczenia | serverless albo klastry, płatność za użycie (DBU) | Spark w ramach pojemności; pojemność F-SKU płatna za czas działania, można ją wstrzymać |
| Orkiestracja | Workflows: DAG, ponowienia, harmonogram, alerty | harmonogram notebooka albo Data Pipeline (jak Azure Data Factory): aktywności połączone „po sukcesie”, ponowienia, alert przy błędzie |
| Kod | job pobiera kod z gałęzi Gita | wheel w Files lub w Environment; integracja obszaru roboczego z Gitem |
| SQL | SQL Warehouse | punkt końcowy analizy SQL lakehouse (T-SQL, tylko odczyt) albo Warehouse |
| Power BI | konektor + Import (u mnie) albo DirectQuery | **Direct Lake**: model czyta Delta prosto z OneLake, bez kopiowania i bez długiego odświeżania |
| Koszt w projekcie | 0 zł (Free Edition z limitami) | 0 zł w wersji próbnej (60 dni) |
| Wygoda (moje wrażenia) | Git folder i job z Gita działają gładko; lineage od ręki | wszystko w jednym miejscu z Power BI; więcej klikania przy bibliotekach (wheel) i podpinaniu lakehouse |

## Co zmieniło się w kodzie

Tylko otoczenie; transformacje, MERGE i testy bez zmian.

| Element | Databricks | Fabric |
| --- | --- | --- |
| Ścieżka surowych plików | `/Volumes/pl_cities/raw/files` | `/lakehouse/default/Files/raw` |
| Nazwa tabeli | `pl_cities.gold.mart_city_score` | `gold.mart_city_score` (domyślny lakehouse) |
| Dostarczenie kodu | Git folder / źródło Git w jobie | wheel w Files (`%pip install`) |
| Liczba notebooków | trzy (zadania joba) | jeden (do porównania) |

## Dlaczego bez joba w Fabric

Codzienny pipeline już działa w Databricks i zasila raport; drugi w Fabric liczyłby to samo, a do tego
regularnie trafiałby na limit API ze współdzielonych adresów IP. Cel tego kroku to porównanie, nie druga produkcja.

## Kiedy co wybrać

**Databricks**, gdy:
- firma jest wielochmurowa albo ma już dane w ADLS / S3;
- liczy się dojrzały Spark, Unity Catalog i kontrola nad obliczeniami;
- zespół to głównie inżynierowie danych i ML.

**Fabric**, gdy:
- firma jest „microsoftowa” (Power BI, Microsoft 365, Azure) i chce jednego miejsca dla danych i raportów;
- raporty mają być świeże bez osobnego odświeżania (Direct Lake);
- zespół jest mieszany: analitycy, Power BI, mniej inżynierii.

**Częsty układ w firmach:** Databricks do ETL, Fabric do warstwy raportowej; OneLake może wskazać tabele
Databricks skrótem (shortcut) albo przez mirroring Unity Catalog, bez kopiowania danych. U mnie działa
podobny podział: Databricks liczy gold, Fabric hostuje model i raport.

## Na rozmowie

„Ten sam pipeline uruchomiłem na Databricks i w Fabric. Zmieniły się tylko ścieżki, nazwy tabel i sposób
dostarczenia kodu, bo logika jest w testowanej paczce, a obie platformy to Spark + Delta. Przy moich danych
czasy są podobne, a różnice wynikają ze startu obliczeń, nie z wydajności. Wybór zależy od firmy:
Databricks przy wielu chmurach i ciężkiej inżynierii, Fabric przy stosie Microsoftu i Power BI.”
