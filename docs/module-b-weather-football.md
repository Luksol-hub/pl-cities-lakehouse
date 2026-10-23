# Moduł B: pogoda a mecze Ekstraklasy

Stan na 2026-10-23. Dane: 4082 mecze z sezonów 2012/13–2025/26, pogoda dzienna w mieście gospodarza.
Tabela gold: `gold_match_weather` (jeden wiersz na czynnik pogodowy i przedział).

## Wyniki

| Czynnik | Przedział | Mecze | Gole na mecz | Wygrane gospodarzy |
| --- | --- | ---: | ---: | ---: |
| Deszcz | sucho (< 1 mm) | 2606 | 2,63 | 44,3% |
| | lekki (1–5 mm) | 946 | 2,66 | 42,6% |
| | mocny (≥ 5 mm) | 530 | 2,70 | 44,7% |
| Temperatura | zimno (< 5°C) | 1099 | 2,56 | 43,8% |
| | umiarkowanie (5–20°C) | 2551 | 2,69 | 44,3% |
| | ciepło (≥ 20°C) | 432 | 2,65 | 42,4% |
| Wiatr | słabo (< 30 km/h) | 3822 | 2,65 | 43,5% |
| | wietrznie (30–50 km/h) | 258 | 2,63 | 51,6% |
| | wichura (≥ 50 km/h) | 2 | 2,00 | 0,0% |

Korelacja Pearsona z liczbą goli: opady −0,004, temperatura 0,038, wiatr −0,015 (praktycznie zero).

## Wnioski

- **Deszcz nie zmienia liczby goli ani przewagi gospodarzy.** Różnice mieszczą się w przypadkowych wahaniach.
- **W zimne dni pada nieco mniej goli** (2,56 wobec 2,69). Różnica jest na granicy przypadku; do sprawdzenia testem statystycznym.
- **Przy wietrze gospodarze wygrywają częściej** (51,6% wobec 43,5%), ale to tylko 258 meczów,
  a przy dziewięciu porównaniach jedno „ciekawe” wyjdzie łatwo przez przypadek. Traktujemy jako trop, nie dowód.
- **Wichura (2 mecze) nic nie mówi:** za mało danych.

Ogólnie: pogoda w dniu meczu ma w Ekstraklasie znikomy związek z wynikiem. Wynik negatywny też jest wynikiem.

## Ograniczenia

- Pogoda jest dzienna: opady to suma z całej doby, a nie z 90 minut meczu.
- Miasto meczu to miasto gospodarza; czasowe przenosiny na inne stadiony pomijamy.
- Średnie w małych przedziałach są niepewne; liczba meczów jest w tabeli, żeby to oceniać.
- To związek, a nie przyczyna: zimą gra się np. na gorszych boiskach, więc mniej goli może wynikać z murawy, nie z temperatury.
