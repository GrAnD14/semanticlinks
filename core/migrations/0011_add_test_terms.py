from django.db import migrations

def add_initial_terms(apps, schema_editor):
    Term = apps.get_model('core', 'Term')
    SemanticLink = apps.get_model('core', 'SemanticLink')
    Discipline = apps.get_model('core', 'Discipline')
    Course = apps.get_model('core', 'Course')

    # Создаем дисциплину
    programming = Discipline.objects.create(
        name="Программирование",
        description="Основы программирования и алгоритмизации"
    )

    # Создаем курс
    python_course = Course.objects.create(
        name="Python для начинающих",
        discipline=programming,
        description="Базовый курс программирования на Python"
    )

    # Создаем термины
    terms_data = [
        {
            'name': 'Переменная',
            'definition': 'Именованная область памяти для хранения данных',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Функция',
            'definition': 'Блок кода, который можно вызывать многократно',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Цикл',
            'definition': 'Конструкция для многократного выполнения кода',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Условный оператор',
            'definition': 'Конструкция для выполнения кода при определенных условиях',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Список',
            'definition': 'Изменяемая последовательность элементов',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Словарь',
            'definition': 'Структура данных для хранения пар ключ-значение',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Модуль',
            'definition': 'Файл с Python кодом, который можно импортировать',
            'discipline': programming,
            'course': python_course
        },
        {
            'name': 'Класс',
            'definition': 'Шаблон для создания объектов в ООП',
            'discipline': programming,
            'course': python_course
        }
    ]

    # Создаем термины
    terms = {}
    for term_data in terms_data:
        term = Term.objects.create(**term_data)
        terms[term_data['name']] = term

    # Создаем связи между терминами
    links = [
        ('Переменная', 'Функция', 'related'),
        ('Переменная', 'Список', 'related'),
        ('Функция', 'Цикл', 'related'),
        ('Функция', 'Условный оператор', 'related'),
        ('Цикл', 'Список', 'related'),
        ('Список', 'Словарь', 'related'),
        ('Модуль', 'Класс', 'related'),
        ('Класс', 'Функция', 'related'),
        ('Переменная', 'Словарь', 'related'),
        ('Функция', 'Модуль', 'related')
    ]

    for source_name, target_name, link_type in links:
        SemanticLink.objects.create(
            source=terms[source_name],
            target=terms[target_name],
            link_type=link_type
        )

def remove_initial_terms(apps, schema_editor):
    Term = apps.get_model('core', 'Term')
    Discipline = apps.get_model('core', 'Discipline')
    Course = apps.get_model('core', 'Course')
    
    # Удаляем все термины, курсы и дисциплины
    Term.objects.all().delete()
    Course.objects.all().delete()
    Discipline.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_neuralnetworklog'),
    ]

    operations = [
        migrations.RunPython(add_initial_terms, remove_initial_terms),
    ] 