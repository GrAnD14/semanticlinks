import requests

url = "https://bothub.chat/api/v2/chat"  # Попробуем эндпоинт для чата
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg1Y2FkOWE4LTcyNjgtNDg3MS04MWUwLTg2NDk3YTY0ZmU1MyIsImlzRGV2ZWxvcGVyIjp0cnVlLCJpYXQiOjE3NDc4NjYwMzAsImV4cCI6MjA2MzQ0MjAzMH0.QWAbUjANDB-gLkBoGTYrj8n7hUDNplVeYG3hfkenpXM",
    "Content-Type": "application/json"
}
data = {
    "messages": [
        {"role": "user", "content": "Дай рекомендации по терминам: Алгоритм, Структура данных"}
    ]
}

response = requests.post(url, headers=headers, json=data)
print("Status code:", response.status_code)
print("Response:", response.text) 