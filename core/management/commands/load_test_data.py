from django.core.management.base import BaseCommand
from core.models import Term, SemanticLink, Course, Discipline, Specialty

class Command(BaseCommand):
    help = 'Загружает тестовые данные в базу'

    def handle(self, *args, **kwargs):
        # Создаем тестовые дисциплины
        discipline = Discipline.objects.create(
            name="Программирование",
            description="Основы программирования и алгоритмизации"
        )

        # Создаем тестовые специальности
        specialty = Specialty.objects.create(
            name="Информационные технологии",
            description="Специальность в области IT"
        )

        # Создаем тестовые курсы
        course = Course.objects.create(
            name="Основы программирования",
            description="Базовый курс программирования",
            discipline=discipline,
            specialty=specialty
        )

        # Создаем тестовые термины
        terms = [
            Term.objects.create(
                name="Алгоритм",
                definition="Конечный набор инструкций, описывающих последовательность действий исполнителя для достижения результата",
                course=course,
                discipline=discipline,
                specialty=specialty
            ),
            Term.objects.create(
                name="Цикл",
                definition="Последовательность команд, которая выполняется многократно",
                course=course,
                discipline=discipline,
                specialty=specialty
            ),
            Term.objects.create(
                name="Условный оператор",
                definition="Оператор, который выполняет различные действия в зависимости от истинности условия",
                course=course,
                discipline=discipline,
                specialty=specialty
            ),
            Term.objects.create(
                name="Массив",
                definition="Структура данных, хранящая набор значений одного типа",
                course=course,
                discipline=discipline,
                specialty=specialty
            ),
            Term.objects.create(
                name="Функция",
                definition="Подпрограмма, которая может быть вызвана из другой части программы",
                course=course,
                discipline=discipline,
                specialty=specialty
            )
        ]

        # Создаем связи между терминами
        links = [
            SemanticLink.objects.create(
                source=terms[0],  # Алгоритм
                target=terms[1],  # Цикл
                link_type="использует"
            ),
            SemanticLink.objects.create(
                source=terms[0],  # Алгоритм
                target=terms[2],  # Условный оператор
                link_type="использует"
            ),
            SemanticLink.objects.create(
                source=terms[0],  # Алгоритм
                target=terms[3],  # Массив
                link_type="работает с"
            ),
            SemanticLink.objects.create(
                source=terms[4],  # Функция
                target=terms[0],  # Алгоритм
                link_type="может содержать"
            ),
            SemanticLink.objects.create(
                source=terms[1],  # Цикл
                target=terms[2],  # Условный оператор
                link_type="может содержать"
            )
        ]

        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно загружены')) 