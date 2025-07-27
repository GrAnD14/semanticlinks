from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
import requests
import re
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

class BothubParseCommandView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get('text', '').strip()
        logger.info(f'Получен запрос: {text}')
        if not text:
            return Response({'error': 'Текст не указан'}, status=400)

        # Подготовка запроса к bothub
        bothub_prompt = f"""Извлеки из запроса преподавателя следующие параметры:
1. Действие (create_term, delete_term, edit_definition, create_link)
2. Название термина(ов)
3. Определение (если есть)
4. Дисциплина (если есть)
5. Курс (если есть)
6. Специальность (если есть)
7. Тип связи (если есть)

Запрос преподавателя: {text}

Верни JSON в формате:
{{
    "action": "действие",
    "term_name": "название термина",
    "term2_name": "название второго термина (для связей)",
    "definition": "определение",
    "discipline": "дисциплина",
    "course": "курс",
    "specialty": "специальность",
    "link_type": "тип связи"
}}

Если какой-то параметр не найден, верни для него null.

Примеры:
1. "Удали термин Квант из базы" -> {{"action": "delete_term", "term_name": "Квант", ...}}
2. "Свяжи термины Квант и Условие как часть" -> {{"action": "create_link", "term_name": "Квант", "term2_name": "Условие", "link_type": "part_of", ...}}"""

        try:
            # Запрос к bothub
            bothub_request = {
                'model': 'gpt-4',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Ты - помощник для извлечения параметров из запросов преподавателей. Возвращай только JSON с параметрами.'
                    },
                    {
                        'role': 'user',
                        'content': bothub_prompt
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 150
            }
            logger.info(f'Отправляем запрос в bothub: {json.dumps(bothub_request, ensure_ascii=False)}')

            bothub_response = requests.post(
                'https://bothub.chat/api/v2/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.BOTHUB_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json=bothub_request
            )

            logger.info(f'Статус ответа bothub: {bothub_response.status_code}')
            logger.info(f'Заголовки ответа bothub: {dict(bothub_response.headers)}')

            if bothub_response.status_code != 200:
                logger.error(f'Ошибка bothub API: {bothub_response.status_code} - {bothub_response.text}')
                return Response({'error': 'Ошибка bothub API'}, status=500)

            bothub_data = bothub_response.json()
            logger.info(f'Полный ответ bothub: {json.dumps(bothub_data, ensure_ascii=False)}')

            params_text = bothub_data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            logger.info(f'Извлеченный текст параметров: {params_text}')

            try:
                params = json.loads(params_text)
                logger.info(f'Распарсенные параметры: {json.dumps(params, ensure_ascii=False)}')
            except json.JSONDecodeError as e:
                logger.error(f'Ошибка парсинга JSON от bothub: {str(e)}')
                logger.error(f'Проблемный текст: {params_text}')
                return Response({'error': 'Ошибка формата ответа'}, status=500)

            # Формируем команду на основе параметров
            command = None
            action = params.get('action')
            logger.info(f'Определено действие: {action}')

            if action == 'create_term':
                command = f"Создай термин: {params.get('term_name', '')}; {params.get('definition', '')}; {params.get('discipline', '')}; {params.get('course', '')}; {params.get('specialty', '')}"
            elif action == 'delete_term':
                command = f"Удали термин: {params.get('term_name', '')}"
            elif action == 'edit_definition':
                command = f"Измени определение для: {params.get('term_name', '')} → {params.get('definition', '')}"
            elif action == 'create_link':
                command = f"Создай связь: {params.get('term_name', '')} —{params.get('link_type', 'related')}→ {params.get('term2_name', '')}"

            if command:
                logger.info(f'Сформирована команда: {command}')
                return Response({'command': command})

            logger.warning('Не удалось определить команду из параметров')
            return Response({'command': None})

        except Exception as e:
            logger.error(f'Ошибка при обработке запроса: {str(e)}', exc_info=True)
            return Response({'error': str(e)}, status=500) 