"""Ekstraklasa teams (names as in football-data.co.uk) and the town of their home stadium.

Used by module B (weather and football). Simplification: a match is played in the home
team's own town. A few clubs temporarily played home games elsewhere while their stadium
was rebuilt (e.g. Warta Poznań in Grodzisk Wielkopolski); we ignore that.
"""

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

# Stadium towns outside the 17 project cities, so we can fetch their weather too.
# Coordinates from the Open-Meteo geocoding API, checked against the voivodeship.
STADIUM_TOWNS = {
    "Bełchatów": (51.37, 19.36),
    "Bielsko-Biała": (49.82, 19.05),
    "Chorzów": (50.31, 18.97),
    "Częstochowa": (50.80, 19.12),
    "Gliwice": (50.30, 18.68),
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
