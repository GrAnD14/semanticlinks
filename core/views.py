from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes
from .serializers import (
    UserSerializer, DisciplineSerializer, CourseSerializer,
    SpecialtySerializer, TermSerializer, SemanticLinkSerializer,
    RegisterSerializer, SavedTermSerializer
)
from .models import (
    Discipline, Course, Specialty, Term, 
    SemanticLink, SavedTerm, NeuralNetworkLog, Profile
)
from .permissions import IsTeacher, IsStudent, IsTeacherOrAdmin
from django.db import models
from rest_framework import serializers
from .bothub import BotHub
import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

class SavedTermViewSet(viewsets.ModelViewSet):
    queryset = SavedTerm.objects.all()
    serializer_class = SavedTermSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return SavedTerm.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if SavedTerm.objects.filter(user=self.request.user, term=serializer.validated_data['term']).exists():
            raise serializers.ValidationError("Этот термин уже сохранен пользователем.")
        serializer.save(user=self.request.user)

    # perform_update и perform_destroy отсутствуют

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Неверные имя пользователя или пароль'}, status=400)

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'email': request.user.email,
            'role': request.user.profile.role,
        })

class DisciplineViewSet(viewsets.ModelViewSet):
    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        else:
            return [IsAuthenticated(), IsTeacherOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'definition']
    ordering_fields = ['name', 'created_by']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def get_queryset(self):
        queryset = Term.objects.all()
        discipline_id = self.request.query_params.get('discipline', None)
        course_id = self.request.query_params.get('course', None)
        specialty_id = self.request.query_params.get('specialty', None)
        created_by = self.request.query_params.get('created_by', None)

        if discipline_id is not None:
            queryset = queryset.filter(discipline_id=discipline_id)
        if course_id is not None:
            queryset = queryset.filter(course_id=course_id)
        if specialty_id is not None:
            queryset = queryset.filter(specialty_id=specialty_id)
        if created_by is not None:
            queryset = queryset.filter(created_by_id=created_by)

        # Если пользователь аутентифицирован, показываем его термины первыми
        if self.request.user.is_authenticated:
            return queryset.order_by(
                models.Case(
                    models.When(created_by=self.request.user, then=0),
                    default=1
                ),
                'name'
            )
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # Проверяем, что пользователь является создателем термина
        if serializer.instance.created_by != self.request.user:
            raise PermissionError("Вы не можете редактировать этот термин")
        serializer.save()
    
class SemanticLinkViewSet(viewsets.ModelViewSet):
    queryset = SemanticLink.objects.all()
    serializer_class = SemanticLinkSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def query_terms(request):
    search_query = request.GET.get('q', '')
    if search_query:
        terms = Term.objects.filter(name__icontains=search_query)
    else:
        terms = Term.objects.all()
    serializer = TermSerializer(terms, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_recommendations(request):
    user = request.user
    terms = request.data.get('terms', [])
    bothub = BotHub()
    recommendations = bothub.get_recommendations(terms)
    return Response(recommendations)

# Новая View для обработки предложения с помощью ИИ и логгирования
class ProcessSentenceView(APIView):
    permission_classes = [IsAuthenticated]  # Теперь требуется аутентификация

    def post(self, request, *args, **kwargs):
        try:
            sentence = request.data.get('sentence')
            if not sentence:
                return Response(
                    {'error': 'Предложение не предоставлено'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"Получено предложение: {sentence}")

            # Создаем запись в логе
            log_entry = NeuralNetworkLog.objects.create(
                input_text=sentence,
                name="Ассоциация-Бот",
                request_time=timezone.now()
            )

            # Получаем термины через BotHub
            bothub = BotHub()
            terms = bothub.get_completion(sentence)
            print(f"Получены термины от BotHub: {terms}")

            # Обновляем лог
            log_entry.output_text = json.dumps(terms)
            log_entry.save()

            # Используем case-insensitive фильтрацию
            matched_terms = list(filter_terms_case_insensitive(terms))

            # Ищем термин, который максимально совпадает с исходным текстом пользователя
            sentence = request.data.get('sentence', '').strip().lower()
            main_term = None
            for t in matched_terms:
                if t.name.strip().lower() == sentence:
                    main_term = t
                    break
            if not main_term and matched_terms:
                main_term = matched_terms[0]

            print(f"[DEBUG] Главный термин: {main_term.name if main_term else None}")

            if main_term:
                links = SemanticLink.objects.filter(
                    models.Q(source=main_term) | models.Q(target=main_term)
                ).select_related('source', 'target')
                related_terms = set()
                for link in links:
                    if link.source == main_term:
                        related_terms.add(link.target)
                    else:
                        related_terms.add(link.source)
                print(f"[DEBUG] Найдено связей: {len(links)}; Связанные термины: {[t.name for t in related_terms]}")
                matched_terms = list(related_terms)
                if not matched_terms:
                    print("[DEBUG] Нет связанных терминов, ответ будет пустым списком.")
            else:
                matched_terms = []
                print("[DEBUG] Главный термин не найден, ответ будет пустым списком.")

            serializer = TermSerializer(matched_terms, many=True)
            print(f"Связанные термины из БД: {[t['name'] for t in serializer.data]}")

            return Response({
                'terms': serializer.data,
                'log_id': log_entry.id
            })

        except Exception as e:
            print(f"Ошибка в ProcessSentenceView: {str(e)}")
            return Response(
                {'error': f'Ошибка при обработке предложения: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

@api_view(['POST'])
@permission_classes([AllowAny])
def process_sentence(request):
    sentence = request.data.get('sentence')
    if not sentence:
        return Response({'error': 'Предложение для анализа не предоставлено.'}, status=status.HTTP_400_BAD_REQUEST)

    print(f"Получено предложение для анализа: {sentence}")

    try:
        # Ищем термины в предложении
        terms = Term.objects.filter(name__icontains=sentence)

        print(f"Результат запроса к БД: {list(terms)}")

        if terms.exists():
            # Возвращаем список объектов терминов с ID и именем
            term_data = [{'id': term.id, 'name': term.name} for term in terms]
            return Response({'terms': term_data})
        else:
            # Если точное совпадение не найдено, попробуйте найти частичное совпадение
            # Это может быть более ресурсоемко, но может дать лучшие результаты
            # Для простоты сейчас вернем пустой список, если нет точного совпадения
            return Response({'terms': []})

    except Exception as e:
        print(f"Ошибка при обработке предложения: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Обновленная функция для case-insensitive фильтрации через ORM
def filter_terms_case_insensitive(terms_from_bothub):
    # Используем __iexact для поиска без учета регистра
    matched_terms = Term.objects.filter(name__in=terms_from_bothub)
    return matched_terms

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_term_connections(request, term_id):
    try:
        term = Term.objects.get(id=term_id)
        
        # Получаем все связи, где термин является источником или целью
        links = SemanticLink.objects.filter(
            models.Q(source=term) | models.Q(target=term)
        ).select_related('source', 'target')
        
        # Собираем все связанные термины
        connected_terms = set()
        for link in links:
            if link.source == term:
                connected_terms.add(link.target)
            else:
                connected_terms.add(link.source)
        
        # Сериализуем данные
        term_serializer = TermSerializer(term)
        links_serializer = SemanticLinkSerializer(links, many=True)
        connected_terms_data = TermSerializer(list(connected_terms), many=True).data
        
        return Response({
            'term': term_serializer.data,
            'links': links_serializer.data,
            'connected_terms': connected_terms_data
        })
    except Term.DoesNotExist:
        return Response(
            {'error': 'Термин не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )