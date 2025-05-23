from flask import Flask, request, jsonify
from openai import OpenAI
import os
from flask_cors import CORS
import json

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app) # Разрешаем CORS для всех маршрутов

# --- Загрузка списка терминов из JSON файла ---
authoritative_terms = [] # Инициализируем пустой список
try:
    # Укажите правильный путь к файлу terms.json, если он отличается
    terms_file_path = 'terms.json' 
    with open(terms_file_path, 'r', encoding='utf-8') as f:
        authoritative_terms = json.load(f)
    print(f"Успешно загружено {len(authoritative_terms)} терминов из {terms_file_path}")
except FileNotFoundError:
    print(f"Ошибка: файл {terms_file_path} не найден. Используется пустой список терминов.")
except json.JSONDecodeError:
    print(f"Ошибка: Некорректный формат JSON в файле {terms_file_path}. Используется пустой список терминов.")
except Exception as e:
    print(f"Произошла ошибка при загрузке терминов из файла: {e}. Используется пустой список терминов.")
# ---------------------------------------------

# Инициализация клиента OpenAI (BotHub)
client = OpenAI(
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg1Y2FkOWE4LTcyNjgtNDg3MS04MWUwLTg2NDk3YTY0ZmU1MyIsImlzRGV2ZWxvcGVyIjp0cnVlLCJpYXQiOjE3NDc4NjYwMzAsImV4cCI6MjA2MzQ0MjAzMH0.QWAbUjANDB-gLkBoGTYrj8n7hUDNplVeYG3hfkenpXM", # Ваш токен Bothub
    base_url="https://bothub.chat/api/v2/openai/v1"
)

@app.route('/process_sentence', methods=['POST'])
def process_sentence():
    data = request.json
    sentence = data.get('sentence')

    if not sentence:
        return jsonify({'error': 'No sentence provided'}), 400

    try:
        # Логика работы с BotHub для выделения терминов (пока без фильтрации)
        prompt = (
            "Выдели из следующего предложения ключевые слова и термины. "
            "Верни только список терминов через запятую, без пояснений и лишнего текста.\n"
            f"Предложение: {sentence}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Обработка ответа от ИИ
        # Ожидаем, что ИИ вернет термины в виде списка строк, например: ["термин1", "термин2"]
        # или просто строку с терминами через запятую/перенос строки.
        # Попытаемся распарсить ответ ИИ в список.
        terms = response.choices[0].message.content.strip()
        extracted_terms = []
        try:
            # Попробуем распарсить как JSON массив
            extracted_terms = json.loads(terms)
            if not isinstance(extracted_terms, list):
                raise ValueError("Expected a list from AI")
        except (json.JSONDecodeError, ValueError):
            # Если не JSON массив, попробуем разбить по запятой или переводу строки
            if terms:
                extracted_terms = [t.strip() for t in terms.replace('\n', ',').split(',') if t.strip()]

        # Фильтрация терминов на основе "авторитетного" списка
        filtered_terms = [term for term in extracted_terms if term.lower() in [auth_term.lower() for auth_term in authoritative_terms]]

        return jsonify({'terms': filtered_terms})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_graph_data', methods=['GET'])
def get_graph_data():
    term = request.args.get('term') # Получаем термин из GET-параметра

    if not term:
        return jsonify({'error': 'No term provided'}), 400

    # Здесь будет логика получения реальных данных графа по термину
    # Пока возвращаем фиктивные данные для тестирования
    mock_nodes = [
        {'id': 1, 'label': term},
        {'id': 2, 'label': 'Связанный термин 1'},
        {'id': 3, 'label': 'Связанный термин 2'}
    ]
    mock_edges = [
        {'from': 1, 'to': 2},
        {'from': 1, 'to': 3}
    ]

    return jsonify({'nodes': mock_nodes, 'edges': mock_edges})

@app.route('/get_term_details', methods=['GET'])
def get_term_details():
    term = request.args.get('term') # Получаем термин из GET-параметра

    if not term:
        return jsonify({'error': 'No term provided'}), 400

    # Здесь будет логика получения реальных деталей термина из вашего источника
    # Пока возвращаем фиктивные детали для тестирования
    mock_details = {
        'term': term,
        'description': f'Это фиктивное описание для термина "{term}".',
        'related_disciplines': ['Дисциплина A', 'Дисциплина B'],
        'related_courses': ['Курс 1', 'Курс 2']
    }

    return jsonify(mock_details)

# Для запуска приложения (только при прямом запуске файла)
if __name__ == '__main__':
    # В режиме отладки Flask автоматически перезагружается при изменениях
    app.run(debug=True) 