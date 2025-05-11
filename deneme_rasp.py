import requests
import json

# Google Apps Script URL (doPost fonksiyonu)
url = 'https://script.google.com/macros/s/AKfycbzXirACZNz02ZJm6JwviIEFLZUYK2uJpghi9TvrmwsEjbwo_QS5i_C80tXP8XmNNbds5g/exec'

# Veri gönderimi
data = {
    "zaman": "2025-05-11 14:30:00",  # Örnek zaman
    "T1": 23.5, "H1": 65,  # Örnek veriler
    "T2": 24.1, "H2": 60,
    "T3": 25.0, "H3": 55,
    "T4": 26.5, "H4": 50,
    "T5": 27.2, "H5": 45,
    "T6": 28.0, "H6": 40,
    "T7": 29.3, "H7": 35,
    "T8": 30.1, "H8": 30,
    "HS1": 12.5,
    "SD1": 0.8
}

# POST isteğini gönder
response = requests.post(url, json=data)

# Gönderim sonrası sonucu kontrol et
print(response.text)

