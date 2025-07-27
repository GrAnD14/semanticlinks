from django.db import models
from django.contrib.auth.models import User

class Discipline(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='disciplines_created')

    def __str__(self):
        return self.name

class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='courses_created')

    def __str__(self):
        return self.name

class Specialty(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Term(models.Model):
    name = models.CharField(max_length=255, unique=True)
    definition = models.TextField()
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='terms_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

    # Проверка, что хотя бы одно поле (discipline, course, specialty) заполнено
    def clean(self):
        if not any([self.discipline, self.course, self.specialty]):
            from django.core.exceptions import ValidationError
            raise ValidationError('Термин должен быть связан хотя бы с одним из: курс, дисциплина или специальность.')

class SemanticLink(models.Model):
    source = models.ForeignKey(Term, related_name='source_links', on_delete=models.CASCADE)
    target = models.ForeignKey(Term, related_name='target_links', on_delete=models.CASCADE)
    link_type = models.CharField(max_length=50) # Например: 'is_a', 'part_of', 'related_to'

    class Meta:
        unique_together = ('source', 'target', 'link_type') # Предотвращает дублирование связей

    def __str__(self):
        return f"{self.source.name} -[{self.link_type}]-> {self.target.name}"

class SavedTerm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'term') # Пользователь может сохранить термин только один раз

    def __str__(self):
        return f"{self.user.username} saved {self.term.name}"

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"

# Модель для логгирования запросов к нейросети
class NeuralNetworkLog(models.Model):
    name = models.CharField(max_length=255)
    input_text = models.TextField()
    output_text = models.TextField(blank=True, null=True)
    request_time = models.DateTimeField()
    response_time = models.DateTimeField(blank=True, null=True)
    successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.request_time}"

class ViewedTerm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'term') # Пользователь может просмотреть уникальный термин только один раз

    def __str__(self):
        return f"{self.user.username} viewed {self.term.name}"

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