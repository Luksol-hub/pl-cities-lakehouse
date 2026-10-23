"""Cities covered by the project: the 17 cities in the NBP housing price data.

Coordinates (latitude, longitude) come from the Open-Meteo geocoding API
and are used to request weather for each city.
"""

CITIES = {
    "Białystok": (53.13, 23.16),
    "Bydgoszcz": (53.12, 18.01),
    "Gdańsk": (54.35, 18.65),
    "Gdynia": (54.52, 18.53),
    "Katowice": (50.26, 19.02),
    "Kielce": (50.87, 20.63),
    "Kraków": (50.06, 19.94),
    "Lublin": (51.25, 22.57),
    "Łódź": (51.77, 19.47),
    "Olsztyn": (53.78, 20.49),
    "Opole": (50.67, 17.93),
    "Poznań": (52.41, 16.93),
    "Rzeszów": (50.04, 22.00),
    "Szczecin": (53.43, 14.55),
    "Warszawa": (52.23, 21.01),
    "Wrocław": (51.10, 17.03),
    "Zielona Góra": (51.94, 15.51),
}

# Voivodeship of every town in the project: the 17 ranked cities and the stadium towns
# of module B. Checked against the Open-Meteo geocoding results.
VOIVODESHIPS = {
    "Bełchatów": "łódzkie",
    "Białystok": "podlaskie",
    "Bielsko-Biała": "śląskie",
    "Bydgoszcz": "kujawsko-pomorskie",
    "Chorzów": "śląskie",
    "Częstochowa": "śląskie",
    "Gdańsk": "pomorskie",
    "Gdynia": "pomorskie",
    "Gliwice": "śląskie",
    "Grodzisk Wielkopolski": "wielkopolskie",
    "Katowice": "śląskie",
    "Kielce": "świętokrzyskie",
    "Kraków": "małopolskie",
    "Legnica": "dolnośląskie",
    "Lublin": "lubelskie",
    "Lubin": "dolnośląskie",
    "Łęczna": "lubelskie",
    "Łódź": "łódzkie",
    "Mielec": "podkarpackie",
    "Nieciecza": "małopolskie",
    "Niepołomice": "małopolskie",
    "Nowy Sącz": "małopolskie",
    "Olsztyn": "warmińsko-mazurskie",
    "Opole": "opolskie",
    "Płock": "mazowieckie",
    "Poznań": "wielkopolskie",
    "Radom": "mazowieckie",
    "Rzeszów": "podkarpackie",
    "Sosnowiec": "śląskie",
    "Szczecin": "zachodniopomorskie",
    "Warszawa": "mazowieckie",
    "Wrocław": "dolnośląskie",
    "Zabrze": "śląskie",
    "Zielona Góra": "lubuskie",
}
