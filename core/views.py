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
    RegisterSerializer, SavedTermSerializer, ProfileSerializer
)
from .models import (
    Discipline, Course, Specialty, Term, 
    SemanticLink, SavedTerm, NeuralNetworkLog, Profile, ViewedTerm
)
from .permissions import IsTeacher, IsStudent, IsTeacherOrAdmin
from django.db import models
from rest_framework import serializers
from .bothub import BotHub
import json
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

User = get_user_model()

class SavedTermViewSet(viewsets.ModelViewSet):
    queryset = SavedTerm.objects.all().select_related('term__discipline', 'term__course', 'term__specialty')
    serializer_class = SavedTermSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['term__name', 'term__definition']
    ordering_fields = ['saved_at', 'term__name']

    def get_queryset(self):
        queryset = SavedTerm.objects.filter(user=self.request.user)

        # Apply filters from query parameters
        discipline_id = self.request.query_params.get('discipline', None)
        course_id = self.request.query_params.get('course', None)
        status_filter = self.request.query_params.get('status', None)
        saved_before = self.request.query_params.get('saved_before', None)
        saved_after = self.request.query_params.get('saved_after', None)

        if discipline_id:
            queryset = queryset.filter(term__discipline_id=discipline_id)

        if course_id:
            queryset = queryset.filter(term__course_id=course_id)

        if status_filter == 'viewed':
            # Фильтруем по наличию соответствующей записи в ViewedTerm
            queryset = queryset.filter(term__viewedterm__user=self.request.user).distinct()
        elif status_filter == 'not_viewed':
            # Фильтруем по отсутствию соответствующей записи в ViewedTerm
            queryset = queryset.exclude(term__viewedterm__user=self.request.user)

        if saved_before:
            # Ожидается формат YYYY-MM-DD
            try:
                from django.utils.dateparse import parse_date
                date_obj = parse_date(saved_before)
                if date_obj:
                    # Включаем термины, сохраненные ДО конца указанного дня
                    queryset = queryset.filter(saved_at__date__lte=date_obj)
            except ValueError:
                pass # Игнорируем некорректную дату

        if saved_after:
            # Ожидается формат YYYY-MM-DD
            try:
                from django.utils.dateparse import parse_date
                date_obj = parse_date(saved_after)
                if date_obj:
                     # Включаем термины, сохраненные ПОСЛЕ начала указанного дня
                    queryset = queryset.filter(saved_at__date__gte=date_obj)
            except ValueError:
                pass # Игнорируем некорректную дату

        # Search is handled by SearchFilter now

        return queryset

    def perform_create(self, serializer):
        if SavedTerm.objects.filter(user=self.request.user, term=serializer.validated_data['term']).exists():
            raise serializers.ValidationError("Этот термин уже сохранен пользователем.")
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object() # Get the SavedTerm instance
        term = instance.term # Get the related Term instance
        user = request.user # Get the current user

        # Find and delete the corresponding ViewedTerm entry
        ViewedTerm.objects.filter(user=user, term=term).delete()
        print(f"[DEBUG] Deleted ViewedTerm for term {term.name} and user {user.username}")

        # Proceed with the default deletion of the SavedTerm instance
        self.perform_destroy(instance)

        return Response(status=status.HTTP_204_NO_CONTENT)

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
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            # If profile does not exist, create a default one
            profile = Profile.objects.create(user=request.user, role='student') # Default role
            print(f"Created missing profile for user {request.user.username}")

        serializer = ProfileSerializer(profile, context={'request': request}) # Pass context to serializer
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user, role='student')
            print(f"Created missing profile for user {user.username} during PATCH")

        print("Request data:", request.data)
        print("Request FILES:", request.FILES)

        data = request.data.copy()
        
        # Handle user data (откат к старой логике)
        if 'first_name' in data:
            user.first_name = data.pop('first_name')[0]
        if 'last_name' in data:
            user.last_name = data.pop('last_name')[0]
        user.save()

        serializer = ProfileSerializer(profile, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            profile.refresh_from_db()
            return Response(ProfileSerializer(profile, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        serializer.save()

class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def get_queryset(self):
        return Term.objects.all()

    def retrieve(self, request, *args, **kwargs):
        # Log term view for authenticated students when retrieving a single term
        instance = self.get_object()
        # REMOVE the automatic logging of ViewedTerm here
        # if request.user.is_authenticated and request.user.profile.role == 'student':
        #     viewed_term, created = ViewedTerm.objects.get_or_create(
        #         user=request.user,
        #         term=instance,
        #         defaults={'viewed_at': timezone.now()}
        #     )
        #     if not created:
        #         # Update timestamp if the entry already exists
        #         viewed_term.viewed_at = timezone.now()
        #         viewed_term.save()
        #     print(f"[DEBUG] Logged/Updated view for term {instance.name} by user {request.user.username}")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            print(f"[DEBUG] Error in perform_update: {str(e)}")
            raise serializers.ValidationError(str(e))
    
class SemanticLinkViewSet(viewsets.ModelViewSet):
    queryset = SemanticLink.objects.all()
    serializer_class = SemanticLinkSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def create(self, request, *args, **kwargs):
        try:
            print(f"[DEBUG] Получен запрос на создание связи: {request.data}")
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print(f"[DEBUG] Ошибка при создании связи: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        try:
            serializer.save()
            print(f"[DEBUG] Создана новая связь: {serializer.instance}")
        except Exception as e:
            print(f"[DEBUG] Ошибка при сохранении связи: {str(e)}")
            raise serializers.ValidationError(str(e))

    def perform_destroy(self, instance):
        try:
            print(f"[DEBUG] Удаление связи: {instance}")
            instance.delete()
        except Exception as e:
            print(f"[DEBUG] Ошибка при удалении связи: {str(e)}")
            raise serializers.ValidationError(str(e))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def query_terms(request):
    try:
        search_query = request.GET.get('q', '')
        print(f"[DEBUG] Received search query: '{search_query}' in query_terms view") # Add debug log
        if search_query:
            terms = Term.objects.filter(name__icontains=search_query)
            print(f"[DEBUG] Executed filter query. Found {terms.count()} terms.") # Add debug log
        else:
            terms = Term.objects.all()
            print(f"[DEBUG] Executed all() query. Found {terms.count()} terms.") # Add debug log

        serializer = TermSerializer(terms, many=True)
        return Response(serializer.data)

    except Exception as e:
        print(f"[DEBUG] Error in query_terms view: {str(e)}") # Add debug log
        return Response(
            {'error': f'Ошибка поиска терминов в базе: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
        fields = ['id', 'source', 'target', 'link_type', 'source_id', 'target_id', 'updated_at']
        

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
        print(f"[DEBUG] Получение связей для термина с ID {term_id}")
        
        # First, get the term
        try:
            term = Term.objects.get(id=term_id)
            print(f"[DEBUG] Найден термин: {term.name}")
        except Term.DoesNotExist:
            print(f"[DEBUG] Термин с ID {term_id} не найден")
            return Response(
                {'error': 'Термин не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle ViewedTerm logging separately
        try:
            if request.user.is_authenticated and request.user.profile.role == 'student':
                viewed_term, created = ViewedTerm.objects.get_or_create(
                    user=request.user,
                    term=term,
                    defaults={'viewed_at': timezone.now()}
                )
                if not created:
                    viewed_term.viewed_at = timezone.now()
                    viewed_term.save()
                print(f"[DEBUG] Обновлена запись просмотра для пользователя {request.user.username}")
        except Exception as e:
            print(f"[DEBUG] Предупреждение: Ошибка при логировании просмотра: {str(e)}")
            # Continue with the main functionality even if logging fails
        
        # Get all links where the term is either source or target
        try:
            links = SemanticLink.objects.filter(
                models.Q(source=term) | models.Q(target=term)
            ).select_related('source', 'target')
            print(f"[DEBUG] Найдено связей: {links.count()}")
        except Exception as e:
            print(f"[DEBUG] Ошибка при получении связей: {str(e)}")
            return Response(
                {'error': f'Ошибка при получении связей: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Collect all connected terms
        connected_terms = set()
        for link in links:
            if link.source == term:
                connected_terms.add(link.target)
            else:
                connected_terms.add(link.source)
        print(f"[DEBUG] Найдено связанных терминов: {len(connected_terms)}")
        
        # Serialize the data
        try:
            term_serializer = TermSerializer(term)
            links_serializer = SemanticLinkSerializer(links, many=True)
            connected_terms_data = TermSerializer(list(connected_terms), many=True).data
            
            response_data = {
                'term': term_serializer.data,
                'links': links_serializer.data,
                'connected_terms': connected_terms_data
            }
            print(f"[DEBUG] Успешно сериализованы данные")
            return Response(response_data)
        except Exception as e:
            print(f"[DEBUG] Ошибка при сериализации данных: {str(e)}")
            return Response(
                {'error': f'Ошибка при сериализации данных: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        print(f"[DEBUG] Неожиданная ошибка в get_term_connections: {str(e)}")
        return Response(
            {'error': f'Неожиданная ошибка: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bothub_parse_terms(request):
    """
    Принимает текст, ищет термины в базе, возвращает найденные термины и их связи.
    Теперь поиск работает с частичными совпадениями и учитывает варианты числа.
    """
    text = request.data.get('text', '')
    if not text:
        return Response({'error': 'Текст не передан'}, status=400)
    bothub = BotHub()
    terms_from_ai = bothub.get_completion(text)
    print(f"[DEBUG] Terms from AI: {terms_from_ai}")

    if not terms_from_ai:
        print("[DEBUG] No terms returned by AI.")
        return Response({'found_terms': []})

    found_terms_set = set()
    found_terms = []
    
    # Сначала ищем частичные совпадения для исходного текста
    partial_matches = Term.objects.filter(name__icontains=text)
    for term in partial_matches:
        if term.id not in found_terms_set:
            found_terms_set.add(term.id)
            found_terms.append(term)
    
    # Затем обрабатываем термины от BotHub
    for t in terms_from_ai:
        t = t.strip()
        if not t:
            continue
            
        # Добавляем варианты числа для поиска
        search_terms = [t]
        if t.endswith('ия'):  # Если заканчивается на "ия" (множественное число)
            search_terms.append(t[:-2] + 'ие')  # Добавляем единственное число
        elif t.endswith('ие'):  # Если заканчивается на "ие" (единственное число)
            search_terms.append(t[:-2] + 'ия')  # Добавляем множественное число
            
        print(f"[DEBUG] Search terms for '{t}': {search_terms}")
            
        for search_term in search_terms:
            # 1. Частичное совпадение (вхождение подстроки)
            icontains = Term.objects.filter(name__icontains=search_term)
            for term in icontains:
                if term.id not in found_terms_set:
                    found_terms_set.add(term.id)
                    found_terms.append(term)
            # 2. Точное совпадение (если не найдено)
            if not icontains:
                exact = Term.objects.filter(name=search_term)
                for term in exact:
                    if term.id not in found_terms_set:
                        found_terms_set.add(term.id)
                        found_terms.append(term)
            # 3. Совпадение без учёта регистра (если не найдено)
            if not icontains and not exact:
                iexact = Term.objects.filter(name__iexact=search_term)
                for term in iexact:
                    if term.id not in found_terms_set:
                        found_terms_set.add(term.id)
                        found_terms.append(term)
                        
    print(f"[DEBUG] Found terms in database: {[term.name for term in found_terms]}")

    result = []
    for term in found_terms:
        links = SemanticLink.objects.filter(
            (models.Q(source=term) | models.Q(target=term))
        )
        relations = []
        for link in links:
            if link.source == term:
                related_term = link.target
                direction = 'out'
            else:
                related_term = link.source
                direction = 'in'
            relations.append({
                'id': related_term.id,
                'name': related_term.name,
                'link_type': link.link_type,
                'direction': direction
            })
        result.append({
            'id': term.id,
            'name': term.name,
            'relations': relations
        })
    return Response({'found_terms': result})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_term_as_viewed(request, term_id):
    """
    Marks a term as viewed for the authenticated user.
    """
    try:
        print(f"Marking term {term_id} as viewed for user {request.user.username}") # Add debug log
        term = Term.objects.get(id=term_id)
        user = request.user

        if user.profile.role != 'student':
            return Response({'error': 'Только студенты могут отмечать термины как изученные.'}, status=status.HTTP_403_FORBIDDEN)

        viewed_term, created = ViewedTerm.objects.get_or_create(
            user=user,
            term=term,
            defaults={'viewed_at': timezone.now()}
        )
        if not created:
            # Update timestamp if the entry already exists
            viewed_term.viewed_at = timezone.now()
            viewed_term.save()

        return Response({'status': 'Термин отмечен как изученный'}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error marking term as viewed: {str(e)}") # Add debug log
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)