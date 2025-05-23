from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Term, Course, Discipline, Specialty, SemanticLink, SavedTerm

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
    
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['role']

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

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name', 'description']

class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = ['id', 'name', 'description']

class CourseSerializer(serializers.ModelSerializer):
    discipline = DisciplineSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'description', 'discipline', 'specialty']

class TermSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    discipline = DisciplineSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True,
        required=False
    )
    discipline_id = serializers.PrimaryKeyRelatedField(
        queryset=Discipline.objects.all(),
        source='discipline',
        write_only=True,
        required=False
    )
    specialty_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(),
        source='specialty',
        write_only=True,
        required=False
    )

    class Meta:
        model = Term
        fields = ['id', 'name', 'definition', 'discipline', 'course', 'specialty', 'created_by', 'course_id', 'discipline_id', 'specialty_id']

    def validate(self, data):
        # Проверяем, что хотя бы одна связь указана
        if not any([data.get('course'), data.get('discipline'), data.get('specialty')]):
            raise serializers.ValidationError(
                "Термин должен быть связан хотя бы с одним из: курс, дисциплина или специальность"
            )
        return data

class SemanticLinkSerializer(serializers.ModelSerializer):
    source = TermSerializer(read_only=True)
    target = TermSerializer(read_only=True)
    source_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(),
        source='source',
        write_only=True
    )
    target_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(),
        source='target',
        write_only=True
    )

    class Meta:
        model = SemanticLink
        fields = ['id', 'source', 'target', 'link_type', 'source_id', 'target_id']

class SavedTermSerializer(serializers.ModelSerializer):
    term = TermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(),
        source='term',
        write_only=True
    )

    class Meta:
        model = SavedTerm
        fields = ['id', 'term', 'saved_at', 'term_id']
        read_only_fields = ['user', 'saved_at']
