# Moduł B: pogoda a mecze Ekstraklasy

Stan na 2026-10-23. Dane: 4082 mecze z sezonów 2012/13–2025/26, pogoda dzienna w mieście, w którym grano mecz.
Tabela gold: `gold_match_weather` (jeden wiersz na czynnik pogodowy i przedział).

## Wyniki

| Czynnik | Przedział | Mecze | Gole na mecz | Wygrane gospodarzy |
| --- | --- | ---: | ---: | ---: |
| Deszcz | sucho (< 1 mm) | 2611 | 2,63 | 44,4% |
| | lekki (1–5 mm) | 940 | 2,67 | 42,4% |
| | mocny (≥ 5 mm) | 531 | 2,69 | 44,6% |
| Temperatura | zimno (< 5°C) | 1096 | 2,56 | 43,5% |
| | umiarkowanie (5–20°C) | 2552 | 2,69 | 44,4% |
| | ciepło (≥ 20°C) | 434 | 2,64 | 42,2% |
| Wiatr | słabo (< 30 km/h) | 3821 | 2,65 | 43,4% |
| | wietrznie (30–50 km/h) | 259 | 2,63 | 51,7% |
| | wichura (≥ 50 km/h) | 2 | 2,00 | 0,0% |

Korelacja Pearsona z liczbą goli: opady −0,006, temperatura 0,038, wiatr −0,013 (praktycznie zero).

## Wnioski

- **Deszcz nie zmienia liczby goli ani przewagi gospodarzy.** Różnice mieszczą się w przypadkowych wahaniach.
- **W zimne dni pada nieco mniej goli** (2,56 wobec 2,69). Różnica jest na granicy przypadku; do sprawdzenia testem statystycznym.
- **Przy wietrze gospodarze wygrywają częściej** (51,7% wobec 43,4%), ale to tylko 259 meczów,
  a przy dziewięciu porównaniach jedno „ciekawe” wyjdzie łatwo przez przypadek. Traktujemy jako trop, nie dowód.
- **Wichura (2 mecze) nic nie mówi:** za mało danych.

Ogólnie: pogoda w dniu meczu ma w Ekstraklasie znikomy związek z wynikiem. Wynik negatywny też jest wynikiem.

## Miasto meczu i przenosiny stadionów

Miasto meczu to miasto gospodarza, z wyjątkiem okresów, gdy klub grał u siebie w innym mieście
(`TEAM_RELOCATIONS` w `common/teams.py`, zastosowane w `silver_matches`). Dotyczy to 168 meczów.
Przenosiny w obrębie tego samego miasta (Ruch na Stadion Śląski) nie zmieniają pogody, więc ich nie ma na liście.

| Drużyna | Okres | Miasto meczów | Mecze | Pewność | Źródła |
| --- | --- | --- | ---: | --- | --- |
| Puszcza Niepołomice | 2023/24 – 1.03.2025 | Kraków (stadion Cracovii) | 27 | wysoka (zgodna liczba meczów ze źródłem) | [Radio Kraków](https://www.radiokrakow.pl/aktualnosci/sport/ekstraklasa-pilkarska-puszcza-wraca-do-domu/), [Wikipedia](https://en.wikipedia.org/wiki/Puszcza_Niepo%C5%82omice) |
| Ruch Chorzów | 2023/24 do 27.10.2023 | Gliwice | 5 | średnia | [Radio Kraków](https://www.radiokrakow.pl/aktualnosci/sport/ruch-z-wisla-zagraja-w-gliwicach-to-juz-nieodwolalne/), [komunikat ESPI](https://www.parkiet.com/komunikaty-espi/art38970511-ruch-chorzow-spolka-akcyjna-zawarcie-istotnej-umowy) |
| Warta Poznań | 2020/21 – 2023/24 | Grodzisk Wielkopolski | 66 | wysoka | [Soccerway](https://pl.soccerway.com/wiadomosci/pi-ka-nozna-betclic-1-liga-warta-poznan-jednak-zostanie-w-grodzisku-ale-zap-aci-kare-za-kazdy-mecz/EwO0ZBmD) |
| Sandecja Nowy Sącz | 2017/18 | Nieciecza | 18 | wysoka | [Wikipedia](https://en.wikipedia.org/wiki/Stadion_Sportowy_Bruk-Bet_Termalica) |
| Raków Częstochowa | 2019/20 – 2020/21 | Bełchatów | 34 | średnia (data powrotu niepotwierdzona) | [Wikipedia](https://en.wikipedia.org/wiki/2020%E2%80%9321_Rak%C3%B3w_Cz%C4%99stochowa_season), [RMF24](https://www.rmf24.pl/fakty/sport/news-twierdza-belchatow-padla-zaglebie-wzielo-rewanz-na-rakowie,nId,4592466) |
| Górnik Łęczna | 2016/17 | Lublin (Arena Lublin) | 18 | niska (cały sezon niepotwierdzony) | [StadiumDB](https://stadiumdb.com/news/2016/07/poland_stadium_relocation_that_might_go_terribly_bad) |

## Ograniczenia

- Pogoda jest dzienna: opady to suma z całej doby, a nie z 90 minut meczu.
- Lista przenosin powstała z wyszukiwania źródeł i może być niepełna; pozycje o średniej i niskiej pewności warto zweryfikować (np. w 90minut.pl).
- Średnie w małych przedziałach są niepewne; liczba meczów jest w tabeli, żeby to oceniać.
- To związek, a nie przyczyna: zimą gra się np. na gorszych boiskach, więc mniej goli może wynikać z murawy, nie z temperatury.
