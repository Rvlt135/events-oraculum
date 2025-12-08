import requests

url = "http://127.0.0.1:1234/v1/chat/completions"

prompt = """
Ты — аналитический движок. Проанализируй данные футбольного матча:

{
  "fair_home": 2.66,
  "fair_draw": 4.00,
  "fair_away": 2.67,
  "market_home": 2.75,
  "market_draw": 3.58,
  "market_away": 2.68
}

Сравни fair vs market и скажи, где есть value.
Ответ короткий.
"""

payload = {
    "model": "meta-llama-3.1-8b-instruct",
    "messages": [
        {"role": "system", "content": "Ты эксперт по спортивной аналитике."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.2
}

resp = requests.post(url, json=payload)
print(resp.json()["choices"][0]["message"]["content"])
