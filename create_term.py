import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'semantic_core.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Term, Course
from rest_framework_simplejwt.tokens import RefreshToken

# Получаем пользователя
user = User.objects.get(username='teach')

# Получаем курс
course = Course.objects.get(id=1)

# Создаем термин
term = Term.objects.create(
    name='Алгоритм',
    definition='Логическая последовательность действий',
    course=course,
    created_by=user
)

print(f'Термин создан: {term.name}') 