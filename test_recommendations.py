import requests

def test_recommendations():
    url = 'http://127.0.0.1:8000/api/recommendations/'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer <your access token>'
    }
    data = {
        'terms': ['Алгоритм', 'Структура данных']
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    print(response.json())

if __name__ == '__main__':
    test_recommendations() 