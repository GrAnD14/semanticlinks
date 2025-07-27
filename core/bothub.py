import requests
from django.conf import settings
from typing import List, Dict
# from core.models import Term # Больше не нужна для этой реализации
import json

class BotHub:
    def __init__(self):
        self.api_key = settings.BOTHUB_API_KEY
        self.api_url = settings.BOTHUB_API_URL

    def get_completion(self, sentence: str) -> List[str]:
        """
        Обрабатывает предложение и возвращает список найденных терминов через BotHub API.
        """
        try:
            print(f"Отправляем запрос к BotHub API {self.api_url}")
            print(f"Заголовки Authorization Bearer {self.api_key[:5]}...") 
            
            # Новый промпт для поддержки недописанных терминов
            prompt = (
                "В предложении могут встречаться неполные или обрезанные термины (например, 'алгорит', 'цикл', 'отор'). "
                "Определи, какие полные термины имелись в виду, и верни их в виде списка через запятую, без пояснений. "
                "Не более 40 слов. "
                f"Предложение: {sentence}"
            )
            data = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            print(f"Тело запроса {json.dumps(data, ensure_ascii=False)}")
            
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=data
            )
            response.raise_for_status()
            data = response.json()
            print(f"Ответ от BotHub API {data}")
            
            # Извлекаем текст ответа и разбиваем на термины
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0].get('message', {}).get('content', '')
                terms = [term.strip() for term in content.split(',')]
                print(f"Извлеченные термины {terms}")
                return terms
            return []
            
        except Exception as e:
            print(f"Ошибка при обработке предложения {str(e)}")
            return []

    def process_query(self, query: str) -> List[Dict]:
        """
        Обрабатывает запрос пользователя и возвращает релевантные термины
        """
        try:
            data = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка при обработке запроса {str(e)}")
            return []

    def get_recommendations(self, terms: List[str]) -> List[Dict]:
        """
        Получает рекомендации на основе списка терминов
        """
        try:
            data = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Рекомендации для терминов {', '.join(terms)}"
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка при получении рекомендаций {str(e)}")
            return []