from django.urls import path
from .views import (
    TermViewSet,
    SavedTermViewSet,
    ProcessSentenceView,
    BothubParseTermsView,
    BothubParseCommandView
)

urlpatterns = [
    path('', TermViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('<int:pk>/', TermViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('<int:pk>/relations/', TermViewSet.as_view({'get': 'relations'})),
    path('saved-terms/', SavedTermViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('saved-terms/<int:pk>/', SavedTermViewSet.as_view({'delete': 'destroy'})),
    path('process-sentence/', ProcessSentenceView.as_view()),
    path('bothub/parse_terms/', BothubParseTermsView.as_view()),
    path('bothub/parse_command/', BothubParseCommandView.as_view(), name='bothub-parse-command'),
] 