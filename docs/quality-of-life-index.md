# Definicja wskaźników

Ustalone: 2026-10-22.

Ranking miast w pytaniu A porównuje dwie rzeczy:

```
Ranking miast  =  dostępność mieszkań (cena za m² vs zarobki)   vs   warunki życia (pogoda + powietrze)
```

## 1. Wskaźnik warunków życia

```
Wskaźnik warunków życia (0–1)
├── Pogoda 50%
│   ├── dni z deszczem   40%
│   ├── dni z mrozem     40%
│   └── dni upalne       20%
└── Powietrze 50%
    └── dni z przekroczoną normą PM10
```

### Składniki

| Składnik | Definicja | Źródło | Kierunek |
| --- | --- | --- | --- |
| Dni z deszczem | dni z opadem ≥ 1 mm w roku | Open-Meteo | mniej = lepiej |
| Dni z mrozem | dni ze średnią temperaturą doby < 0°C w roku | Open-Meteo | mniej = lepiej |
| Dni upalne | dni ze średnią temperaturą doby ≥ 22°C w roku | Open-Meteo | mniej = lepiej |
| Dni z przekroczoną normą PM10 | dni ze średnim stężeniem PM10 > 50 µg/m³ w roku | GIOŚ (do pobrania) | mniej = lepiej |

**PM10 (GIOŚ):** liczba dni z PM10 > 50 µg/m³ pochodzi z rocznych statystyk GIOŚ
(kolumna „L>50 (S24)”), osobno dla każdej stacji. Wartość dla miasta liczymy w silver:

1. Bierzemy tylko stacje z kompletnością pomiarów ≥ 75% w danym roku.
2. Gdy stacja mierzy dwiema metodami, bierzemy manualną (`24g`, metoda referencyjna);
   automatyczną (`1g`) tylko wtedy, gdy manualnej brak albo ma kompletność < 75%.
3. Wartość dla miasta to mediana ze stacji, odporna na jedną skrajną stację (np. przy ruchliwej ulicy).
4. Gdy w danym roku żadna stacja w mieście nie spełnia warunków, zostawiamy brak danych
   (np. Opole 2007, Zielona Góra 2010). W gold takie miasto **pomijamy w rankingu tego roku**
   (decyzja z 2026-10-23): wskaźnik z połową składników nie byłby porównywalny z resztą.

Opad poniżej 1 mm to mżawka, którą trudno zauważyć, więc nie liczy się jako dzień z deszczem.
Średnia temperatura doby ≥ 22°C oznacza zwykle ponad 28°C w ciągu dnia.

### Odrzucone składniki

- **Dni wietrzne (porywy ≥ 40 km/h):** prawie wszędzie 1–3 dni w roku, poza wybrzeżem (Gdynia 14, Gdańsk 9).
  Składnik karałby tylko Trójmiasto, nie różnicując reszty.
- **Średnia temperatura zimą:** mówi prawie to samo co dni z mrozem; oba naraz liczyłyby zimę podwójnie.

### Normalizacja i agregacja

1. Każdy składnik liczymy dla miasta i roku.
2. Normalizacja **min-max** do skali 0–1 w obrębie danego roku, odwrócona, bo mniej znaczy lepiej:
   `wynik = (max - wartość) / (max - min)`. Najlepsze miasto w danym roku dostaje 1, najgorsze 0.
3. Wynik pogody to średnia ważona składników pogodowych (40/40/20).
4. Wskaźnik warunków życia = 50% pogoda + 50% powietrze.

Normalizacja w obrębie roku porównuje miasta między sobą, a nie z ideałem.
Wynik 1 znaczy „najlepsze z 17 miast w tym roku”, a nie „idealne warunki”.

## 2. Dostępność mieszkań

```
Dostępność = średnie miesięczne wynagrodzenie brutto / cena transakcyjna za m²
```

Wynik czytamy jako „ile m² mieszkania kupisz za jedną średnią pensję”. Więcej znaczy lepiej.

- **Wynagrodzenia:** GUS BDL, przeciętne miesięczne wynagrodzenie brutto w mieście (dane roczne, do pobrania).
- **Ceny:** NBP, ceny transakcyjne za m²; średnia z czterech kwartałów danego roku.
  Gold liczy dostępność **osobno dla rynku pierwotnego i wtórnego** (decyzja z 2026-10-23);
  wybór lub uśrednienie rynków dzieje się w Power BI (średnia, nie suma: sumowanie cen za m² nie ma sensu).

Zarobki nie wchodzą do wskaźnika warunków życia, bo mierzą co innego: na ile mieszkańców stać.
Służą do urealnienia cen, bo ta sama cena za m² znaczy co innego przy różnych zarobkach.

## 3. Ranking miast (decyzja z 2026-10-23)

Tabela `mart_city_score` ma wiersz na rynek, miasto i rok, a w nim:

- oba wskaźniki obok siebie: wskaźnik warunków życia (0–1) i m² za pensję,
- **ocenę dostępności** 0–1: min-max w obrębie roku i rynku (więcej m² za pensję = lepiej),
- **wynik końcowy** = 50% wskaźnik warunków życia + 50% ocena dostępności,
- miejsca w rankingu (1 = najlepsze) dla warunków życia, dostępności i wyniku końcowego, w obrębie roku i rynku.

W Power BI można pokazać gotowy ranking albo wykres punktowy: warunki życia na jednej osi, dostępność na drugiej.

## 4. Zakres i ograniczenia

- Ranking liczymy dla pełnych lat (od 2007), żeby nie porównywać niepełnego roku z pełnym.
- Różnice pogodowe między miastami są niewielkie, bo Polska to jeden klimat:
  dni z deszczem wahają się od ok. 122 do 143 w roku (średnia z lat 2007–2025).
- Normalizacja min-max w obrębie roku daje **ranking względny**: wynik 0 znaczy „najgorsze z miast w tym roku”,
  a nie „złe warunki”. W 2025 Poznań ma ocenę powietrza 0,04 przy 26,5 dniach smogu, a w 2007 Kraków
  miał 0,0 przy 157 dniach. Do porównań w czasie służą surowe liczby dni, nie oceny 0–1.
  Min-max jest też wrażliwy na jedno skrajne miasto, które „rozciąga” skalę dla reszty.
- Wagi są subiektywnym wyborem autora. Wynik to ranking według przyjętej definicji, a nie dowód przyczynowości.

## Wartości poglądowe (pogoda, średnia roczna 2007–2025)

| Miasto | Dni z deszczem | Dni z mrozem | Dni upalne |
| --- | ---: | ---: | ---: |
| Białystok | 132 | 59 | 17 |
| Bydgoszcz | 122 | 40 | 18 |
| Gdańsk | 130 | 36 | 10 |
| Gdynia | 140 | 36 | 8 |
| Katowice | 138 | 47 | 20 |
| Kielce | 132 | 56 | 19 |
| Kraków | 142 | 46 | 21 |
| Lublin | 131 | 52 | 20 |
| Łódź | 130 | 51 | 19 |
| Olsztyn | 134 | 55 | 12 |
| Opole | 133 | 41 | 23 |
| Poznań | 124 | 37 | 21 |
| Rzeszów | 143 | 47 | 24 |
| Szczecin | 129 | 32 | 13 |
| Warszawa | 132 | 46 | 23 |
| Wrocław | 129 | 36 | 23 |
| Zielona Góra | 126 | 37 | 23 |
