import requests
import json

url = "https://script.google.com/macros/s/AKfycbyVM121fuxuYy5QoI7R-EpoK5q9tEmOhDFCINSKuybFG7DNtYMKx0dJxDhOJSmw0BqNng/exec"  # Buraya kendi Web App linkini yaz
headers = {"Content-Type": "application/json"}

data = {
    "api_key": "GIZLI_ANAHTAR_123",
    "zaman": "2025-05-11 12:34:56",
    "T1": 25.3, "H1": 60,
    "T2": 25.4, "H2": 61,
    "T3": 25.2, "H3": 59,
    "T4": 25.1, "H4": 58,
    "T5": 25.0, "H5": 57,
    "T6": 24.9, "H6": 56
}

response = requests.post(url, data=json.dumps(data), headers=headers)
print(response.text)

