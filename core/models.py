from django.db import models
from django.contrib.auth.models import User

class Discipline(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Course(models.Model):
    name = models.CharField(max_length=100)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Specialty(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Term(models.Model):
    name = models.CharField(max_length=100)
    definition = models.TextField()
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

class SemanticLink(models.Model):
    LINK_TYPES = (
        ('related', 'Связан с'),
        ('example', 'Пример'),
        ('synonym', 'Синоним'),
        ('antonym', 'Антоним'),
    )
    source = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='source_links')
    target = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='target_links')
    link_type = models.CharField(max_length=20, choices=LINK_TYPES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.source} -[{self.link_type}]-> {self.target}"

class SavedTerm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'term'], name='saved_term_user_term_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} saved {self.term.name}"

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"

# Модель для логгирования запросов к нейросети
class NeuralNetworkLog(models.Model):
    # Поля из вашей схемы "Нейронная_сеть"
    # Учитываем, что у нас уже есть модели Discipline, Course, Specialty, Profile и User
    # Код_сети - можем использовать auto-generated ID модели
    name = models.CharField(max_length=100, help_text="Название модели ИИ (например, gpt-4o)") # Название_модели
    version = models.CharField(max_length=50, blank=True, help_text="Версия модели ИИ") # Версия_модели (опционально)
    description = models.TextField(blank=True, help_text="Описание модели ИИ") # Описание_модели (опционально)
    input_text = models.TextField(help_text="Входной текст запроса от пользователя") # Входное_ключевое_слово (переименовано для ясности)
    output_text = models.TextField(help_text="Результат обработки нейросетью (например, список терминов)") # Результат_текстового_вывода_или_списка_терминов
    request_time = models.DateTimeField(auto_now_add=True, help_text="Дата и время запроса") # Дата_и_время_запроса
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Пользователь, отправивший запрос") # Код_профиля (через связь с User)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, help_text="Курс, связанный с запросом (если применимо)") # Код_курса
    discipline = models.ForeignKey('Discipline', on_delete=models.SET_NULL, null=True, blank=True, help_text="Дисциплина, связанная с запросом (если применимо)") # Код_дисциплины (добавлено для полноты)
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True, help_text="Специальность, связанная с запросом (если применимо)") # Код_специальности
    profile_type = models.ForeignKey('Profile', on_delete=models.SET_NULL, null=True, blank=True, help_text="Тип профиля пользователя (Студент/Преподаватель)") # Код_типа_профиля (через связь с Profile)

    def __str__(self):
        return f"Log for User {self.user.username if self.user else 'Anonymous'} at {self.request_time.strftime('%Y-%m-%d %H:%M')}"

def create_fake_terms_and_links():
    """
    Вспомогательная функция для быстрого наполнения базы тестовыми терминами и связями.
    """
    from core.models import Term, SemanticLink
    # Очищаем старые данные
    SemanticLink.objects.all().delete()
    Term.objects.all().delete()
    # Создаем термины
    t1 = Term.objects.create(name='Термин 1', definition='Описание 1')
    t2 = Term.objects.create(name='Термин 2', definition='Описание 2')
    t3 = Term.objects.create(name='Термин 3', definition='Описание 3')
    t4 = Term.objects.create(name='Термин 4', definition='Описание 4')
    # Создаем связи
    SemanticLink.objects.create(source=t1, target=t2, link_type='related')
    SemanticLink.objects.create(source=t2, target=t3, link_type='related')
    SemanticLink.objects.create(source=t3, target=t4, link_type='related')
    SemanticLink.objects.create(source=t4, target=t1, link_type='related')
    print('Фиктивные термины и связи успешно созданы.')