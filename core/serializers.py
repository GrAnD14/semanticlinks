from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Term, Course, Discipline, Specialty, SemanticLink, SavedTerm
from django.db import models

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['student', 'teacher'], default='student')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', 'student')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        Profile.objects.create(user=user, role=role)
        return user
    
class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name', 'description']

class CourseSerializer(serializers.ModelSerializer):
    discipline = serializers.SerializerMethodField()
    specialty = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'description', 'discipline', 'specialty']

    def get_discipline(self, obj):
        if obj.discipline:
            return {'id': obj.discipline.id, 'name': obj.discipline.name, 'description': obj.discipline.description}
        return None

    def get_specialty(self, obj):
        if obj.specialty:
            return {'id': obj.specialty.id, 'name': obj.specialty.name, 'description': obj.specialty.description}
        return None

class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True, allow_null=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    # Поля для чтения (возвращают полные объекты Course/Specialty)
    course = CourseSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)

    # Поля для записи (принимают только ID)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True,
        required=False,
        allow_null=True
    )
    specialty_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(),
        source='specialty',
        write_only=True,
        required=False,
        allow_null=True
    )
    profile_picture_url = serializers.SerializerMethodField(read_only=True)

    # Новые поля для статистики изучения терминов
    today_studied_count = serializers.SerializerMethodField()
    total_studied_count = serializers.SerializerMethodField()
    disciplines_progress = serializers.SerializerMethodField()
    last_viewed_term = serializers.SerializerMethodField()
    weekly_studied_count = serializers.SerializerMethodField()
    created_terms_count = serializers.SerializerMethodField()
    related_disciplines_count = serializers.SerializerMethodField()
    terms_without_links_count = serializers.SerializerMethodField()
    last_added_term = serializers.SerializerMethodField()
    last_edited_term = serializers.SerializerMethodField()
    last_created_link = serializers.SerializerMethodField()

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            url = obj.profile_picture.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_today_studied_count(self, obj):
        # Количество уникальных терминов, просмотренных сегодня
        from django.utils import timezone
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        viewed_today = obj.user.viewedterm_set.filter(viewed_at__gte=today_start)
        count = viewed_today.values('term').distinct().count()
        return count

    def get_total_studied_count(self, obj):
        # Общее количество уникальных просмотренных терминов
        viewed_terms_ids = obj.user.viewedterm_set.values_list('term_id', flat=True)
        # Используем set для получения уникальных ID и затем считаем их количество
        # Удаляем saved_terms_ids из расчета
        all_studied_ids = set(list(viewed_terms_ids))
        return len(all_studied_ids)

    def get_disciplines_progress(self, obj):
        # Прогресс по дисциплинам на основе изученных/сохраненных терминов
        user = obj.user
        viewed_terms_ids = user.viewedterm_set.values_list('term_id', flat=True)
        saved_terms_ids = user.savedterm_set.values_list('term_id', flat=True)
        all_studied_ids = list(set(list(viewed_terms_ids) + list(saved_terms_ids)))

        if not all_studied_ids:
            return [] # Если нет изученных терминов, возвращаем пустой список

        # Получаем все изученные термины с их дисциплинами
        studied_terms = Term.objects.filter(id__in=all_studied_ids).select_related('discipline')

        # Группируем термины по дисциплинам
        disciplines_data = {}
        for term in studied_terms:
            if term.discipline:
                discipline_id = term.discipline.id
                if discipline_id not in disciplines_data:
                    disciplines_data[discipline_id] = {
                        'id': discipline_id,
                        'name': term.discipline.name,
                        'studied_count': 0,
                        'total_count': 0
                    }
                disciplines_data[discipline_id]['studied_count'] += 1

        # Получаем общее количество терминов для каждой из этих дисциплин
        # Это более эффективно, чем считать для каждой дисциплины по отдельности в цикле
        discipline_ids = disciplines_data.keys()
        total_terms_in_disciplines = Term.objects.filter(discipline__id__in=discipline_ids)

        for term in total_terms_in_disciplines:
            if term.discipline and term.discipline.id in disciplines_data:
                disciplines_data[term.discipline.id]['total_count'] += 1

        # Форматируем результат
        result = []
        for discipline_id, data in disciplines_data.items():
            progress_percent = (data['studied_count'] / data['total_count']) * 100 if data['total_count'] > 0 else 0
            result.append({
                'id': data['id'],
                'name': data['name'],
                'studied_count': data['studied_count'],
                'total_count': data['total_count'],
                'progress_percent': round(progress_percent, 2) # Округляем до 2 знаков после запятой
            })

        return result

    def get_last_viewed_term(self, obj):
        # Последний просмотренный термин и дата
        last_viewed = obj.user.viewedterm_set.order_by('-viewed_at').first()
        if last_viewed:
            return {
                'name': last_viewed.term.name,
                'viewed_at': last_viewed.viewed_at.strftime('%Y-%m-%d %H:%M') # Форматируем дату
            }
        return None

    def get_weekly_studied_count(self, obj):
        # Количество уникальных терминов, просмотренных за последнюю неделю
        from django.utils import timezone
        last_week_start = timezone.now() - timezone.timedelta(days=7)
        return obj.user.viewedterm_set.filter(viewed_at__gte=last_week_start).values('term').distinct().count()

    def get_created_terms_count(self, obj):
        # Количество терминов, созданных этим пользователем (актуально для преподавателя)
        return Term.objects.filter(created_by=obj.user).count()

    def get_related_disciplines_count(self, obj):
        # Количество уникальных дисциплин, к которым относятся созданные преподавателем термины
        return Term.objects.filter(created_by=obj.user, discipline__isnull=False).values('discipline').distinct().count()

    def get_terms_without_links_count(self, obj):
        # Количество терминов, созданных этим преподавателем, у которых нет ни одной семантической связи
        created_terms = Term.objects.filter(created_by=obj.user)
        terms_with_links = set(SemanticLink.objects.filter(
            models.Q(source__in=created_terms) | models.Q(target__in=created_terms)
        ).values_list('source', flat=True)) | set(SemanticLink.objects.filter(
            models.Q(source__in=created_terms) | models.Q(target__in=created_terms)
        ).values_list('target', flat=True))
        return created_terms.exclude(id__in=terms_with_links).count()

    def get_last_added_term(self, obj):
        term = Term.objects.filter(created_by=obj.user).order_by('-created_at').first()
        if term:
            return {'name': term.name, 'created_at': term.created_at.strftime('%Y-%m-%d %H:%M') if term.created_at else ''}
        return None

    def get_last_edited_term(self, obj):
        term = Term.objects.filter(created_by=obj.user).order_by('-updated_at').first()
        if term:
            return {'name': term.name, 'updated_at': term.updated_at.strftime('%Y-%m-%d %H:%M') if term.updated_at else ''}
        return None

    def get_last_created_link(self, obj):
        link = SemanticLink.objects.filter(source__created_by=obj.user).order_by('-id').first()
        if link:
            return {'name': f"{link.source.name} → {link.target.name}", 'created_at': getattr(link, 'created_at', '')}
        return None

    class Meta:
        model = Profile
        fields = [
            'role', 'first_name', 'last_name', 'patronymic',
            'profile_picture', 'profile_picture_url',
            'course', 'specialty',
            'course_id', 'specialty_id',
            'today_studied_count', 'total_studied_count', 'disciplines_progress',
            'last_viewed_term', 'weekly_studied_count',
            'created_terms_count', 'related_disciplines_count', 'terms_without_links_count',
            'last_added_term', 'last_edited_term', 'last_created_link',
        ]
        read_only_fields = ['role', 'today_studied_count', 'total_studied_count', 'disciplines_progress', 'last_viewed_term', 'weekly_studied_count', 'created_terms_count', 'related_disciplines_count', 'terms_without_links_count', 'last_added_term', 'last_edited_term', 'last_created_link']

    def update(self, instance, validated_data):
        print("--- ProfileSerializer Update Start ---")
        print("Validated data:", validated_data)
        
        # Обновляем связанные поля пользователя
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
        instance.user.save()
        
        # Handle profile picture
        profile_picture = validated_data.pop('profile_picture', None)
        if profile_picture is not None:
            # If a new file is uploaded, save it
            if hasattr(profile_picture, 'file'):
                instance.profile_picture = profile_picture
            # If None is explicitly sent, clear the picture
            elif profile_picture is None:
                instance.profile_picture = None

        # Handle other fields (patronymic, course, specialty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        profile_role = self.initial_data.get('role', 'student')
        Profile.objects.create(user=user, role=profile_role)
        
        return user

class DisciplineSerializer(serializers.ModelSerializer):
    total_terms = serializers.SerializerMethodField()

    class Meta:
        model = Discipline
        fields = ['id', 'name', 'description', 'total_terms']

    def get_total_terms(self, obj):
        # obj here is a Discipline instance
        return obj.term_set.count()

class TermSerializer(serializers.ModelSerializer):
    # Поля для чтения (возвращают полные объекты)
    course = CourseSerializer(read_only=True)
    discipline = DisciplineSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    links_count = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(read_only=True)

    # Поля для записи (принимают только ID)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True,
        required=False,
        allow_null=True
    )
    discipline_id = serializers.PrimaryKeyRelatedField(
        queryset=Discipline.objects.all(),
        source='discipline',
        write_only=True,
        required=False,
        allow_null=True
    )
    specialty_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(),
        source='specialty',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Term
        fields = [
            'id', 'name', 'definition',
            'discipline', 'course', 'specialty',
            'discipline_id', 'course_id', 'specialty_id',
            'created_by', 'created_at', 'links_count', 'updated_at'
        ]

    def get_links_count(self, obj):
        return obj.source_links.count() + obj.target_links.count()

    def validate(self, data):
        print("[DEBUG] TermSerializer validate method received data:", data)
        print("[DEBUG] Data keys:", data.keys())
        print("[DEBUG] Data values:", {k: str(v) for k, v in data.items()})
        
        # Проверяем, что хотя бы одно из полей заполнено
        if not any([
            data.get('discipline'),
            data.get('course'),
            data.get('specialty')
        ]):
            print("[DEBUG] Validation failed: no category fields present")
            raise serializers.ValidationError(
                "Термин должен быть связан хотя бы с одним из: курс, дисциплина или специальность"
            )
        print("[DEBUG] Validation passed")
        return data

    def create(self, validated_data):
        print("[DEBUG] TermSerializer create method received data:", validated_data)
        # Получаем текущего пользователя из контекста
        user = self.context['request'].user
        # Добавляем created_by в validated_data
        validated_data['created_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        print("[DEBUG] TermSerializer update method received data:", validated_data)
        print("[DEBUG] Current instance:", instance.__dict__)
        return super().update(instance, validated_data)

class SemanticLinkSerializer(serializers.ModelSerializer):
    source = TermSerializer(read_only=True)
    target = TermSerializer(read_only=True)
    source_id = serializers.IntegerField(write_only=True)
    target_id = serializers.IntegerField(write_only=True)
    link_type = serializers.CharField(max_length=50)

    class Meta:
        model = SemanticLink
        fields = ['id', 'source', 'target', 'link_type', 'source_id', 'target_id']

    def validate(self, data):
        # Проверяем, что source_id и target_id не равны
        if data.get('source_id') == data.get('target_id'):
            raise serializers.ValidationError("Термин не может быть связан сам с собой")
        
        # Проверяем существование терминов
        try:
            source_term = Term.objects.get(id=data.get('source_id'))
            target_term = Term.objects.get(id=data.get('target_id'))
        except Term.DoesNotExist:
            raise serializers.ValidationError("Один из терминов не найден")
        
        # Проверяем, не существует ли уже такая связь
        if SemanticLink.objects.filter(
            source=source_term,
            target=target_term,
            link_type=data.get('link_type')
        ).exists():
            raise serializers.ValidationError("Такая связь уже существует")
        
        return data

    def create(self, validated_data):
        try:
            source_term = Term.objects.get(id=validated_data['source_id'])
            target_term = Term.objects.get(id=validated_data['target_id'])
            
            link = SemanticLink.objects.create(
                source=source_term,
                target=target_term,
                link_type=validated_data['link_type']
            )
            return link
        except Exception as e:
            raise serializers.ValidationError(f"Ошибка при создании связи: {str(e)}")

class SavedTermSerializer(serializers.ModelSerializer):
    term = TermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(),
        source='term',
        write_only=True
    )
    is_viewed = serializers.SerializerMethodField()

    class Meta:
        model = SavedTerm
        fields = ['id', 'term', 'saved_at', 'term_id', 'is_viewed']
        read_only_fields = ['user', 'saved_at']

    def get_is_viewed(self, obj):
        # Проверяем, просмотрен ли этот термин текущим пользователем
        user = self.context['request'].user
        return obj.term.viewedterm_set.filter(user=user).exists()

