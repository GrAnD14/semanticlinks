from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DisciplineViewSet, CourseViewSet, SpecialtyViewSet, TermViewSet,
    SemanticLinkViewSet, SavedTermViewSet,
    query_terms, get_recommendations, RegisterView, LoginView, UserDetailView, ProcessSentenceView, process_sentence, # Импортируем правильные классы и функцию process_sentence
    get_term_connections
)

router = DefaultRouter()
router.register(r'disciplines', DisciplineViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'specialties', SpecialtyViewSet)
router.register(r'terms', TermViewSet)
router.register(r'links', SemanticLinkViewSet)
router.register(r'saved-terms', SavedTermViewSet)

urlpatterns = [
    path('', include(router.urls)), # Все ViewSetы доступны по /api/...

    # Маршруты для терминов
    path('terms/query/', query_terms, name='query-terms'),
    path('terms/<int:term_id>/connections/', get_term_connections, name='term-connections'),

    # Маршруты для аутентификации
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('users/me/', UserDetailView.as_view(), name='user-me'), # Используем UserDetailView

    # Маршруты для рекомендаций и обработки предложений
    path('recommendations/', get_recommendations, name='get_recommendations'),
    path('process-sentence/', process_sentence, name='process_sentence'),
]