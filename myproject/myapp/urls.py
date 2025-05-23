from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, HistoryViewSet
from .auth_views import LoginView, LogoutView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'histories', HistoryViewSet)
urlpatterns = [
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('history/', views.history, name='history'),
    path('myadmin/', views.myadmin, name='myadmin'),
    path('history-detail/', views.history_detail, name='history_detail'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('contact/', views.contact, name='contact'),
    path('', include(router.urls)),
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('auth/logout/', LogoutView.as_view(), name='api_logout'),
    path('api/text-to-speech/', views.text_to_speech, name='text_to_speech'),
]
