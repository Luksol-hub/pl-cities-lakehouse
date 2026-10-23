"""Ekstraklasa teams (names as in football-data.co.uk) and the town of their home stadium.

Used by module B (weather and football). `TEAM_TOWNS` is each club's own town;
`TEAM_RELOCATIONS` lists periods when a club played home games in another town
(stadium too small or under reconstruction). Only changes of town matter for the weather,
so a move to another stadium in the same town (Ruch to Stadion Śląski) is not listed.
"""

from datetime import date

TEAM_TOWNS = {
    "Arka Gdynia": "Gdynia",
    "Cracovia": "Kraków",
    "GKS Belchatow": "Bełchatów",
    "GKS Katowice": "Katowice",
    "Gornik Z.": "Zabrze",
    "Gornik Zabrze": "Zabrze",
    "Jagiellonia": "Białystok",
    "Korona Kielce": "Kielce",
    "LKS Lodz": "Łódź",
    "Lech Poznan": "Poznań",
    "Lechia Gdansk": "Gdańsk",
    "Leczna": "Łęczna",
    "Legia": "Warszawa",
    "Legnica": "Legnica",
    "Motor Lublin": "Lublin",
    "Piast Gliwice": "Gliwice",
    "Podbeskidzie": "Bielsko-Biała",
    "Pogon Szczecin": "Szczecin",
    "Polonia Warszawa": "Warszawa",
    "Puszcza": "Niepołomice",
    "Radomiak Radom": "Radom",
    "Rakow": "Częstochowa",
    "Ruch": "Chorzów",
    "Ruch Chorzow": "Chorzów",
    "Sandecja Nowy S.": "Nowy Sącz",
    "Slask Wroclaw": "Wrocław",
    "Stal Mielec": "Mielec",
    "Termalica B-B.": "Nieciecza",
    "Warta Poznan": "Poznań",
    "Widzew Lodz": "Łódź",
    "Wieczysta Krakow": "Kraków",
    "Wisla": "Kraków",
    "Wisla Plock": "Płock",
    "Zaglebie": "Lubin",
    "Zaglebie Sosnowiec": "Sosnowiec",
    "Zawisza": "Bydgoszcz",
}

# (team, first day, last day, town) of home games played away from the club's own town.
# Researched on 2026-10-23 (sources in docs/module-b-weather-football.md); confidence noted.
TEAM_RELOCATIONS = [
    # Own stadium failed top-flight licensing; played at Cracovia's ground. High confidence.
    ("Puszcza", date(2023, 7, 1), date(2025, 3, 1), "Kraków"),
    # Played in Gliwice until the move to Stadion Śląski (Chorzów) on 28.10.2023. Medium.
    ("Ruch Chorzow", date(2023, 7, 1), date(2023, 10, 27), "Gliwice"),
    # Every Ekstraklasa season after promotion was played in Grodzisk Wielkopolski. High.
    ("Warta Poznan", date(2020, 7, 1), date(2024, 6, 30), "Grodzisk Wielkopolski"),
    # Own stadium below league requirements in the only Ekstraklasa season. High.
    ("Sandecja Nowy S.", date(2017, 7, 1), date(2018, 6, 30), "Nieciecza"),
    # Stadium in Częstochowa rebuilt; exact return date not confirmed. Medium.
    ("Rakow", date(2019, 7, 1), date(2021, 6, 30), "Bełchatów"),
    # Club moved to Arena Lublin in 2016; whole season not confirmed. Low.
    ("Leczna", date(2016, 7, 1), date(2017, 6, 30), "Lublin"),
]

# Stadium towns outside the 17 project cities, so we can fetch their weather too.
# Coordinates from the Open-Meteo geocoding API, checked against the voivodeship.
STADIUM_TOWNS = {
    "Bełchatów": (51.37, 19.36),
    "Bielsko-Biała": (49.82, 19.05),
    "Chorzów": (50.31, 18.97),
    "Częstochowa": (50.80, 19.12),
    "Gliwice": (50.30, 18.68),
    # Searching "Grodzisk" returns Grodzisk Mazowiecki first; this is the Wielkopolski one.
    "Grodzisk Wielkopolski": (52.23, 16.37),
    "Legnica": (51.21, 16.16),
    "Lubin": (51.40, 16.20),
    "Łęczna": (51.30, 22.88),
    "Mielec": (50.29, 21.42),
    "Nieciecza": (50.15, 20.85),
    "Niepołomice": (50.04, 20.22),
    "Nowy Sącz": (49.62, 20.70),
    "Płock": (52.55, 19.71),
    "Radom": (51.40, 21.15),
    "Sosnowiec": (50.29, 19.10),
    "Zabrze": (50.32, 18.79),
}
