from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.contrib.auth import views as auth_views

router = DefaultRouter()

router.register(r'jobs', views.JobViewSet, basename='job')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'apply', views.JobApplicationViewSet, basename='apply')
router.register(r'technology', views.TechnologyViewSet, basename='technology')
router.register(r'save_job', views.SaveJobViewSet, basename='save_job')
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'statistics', views.EmployerStatisticsViewSet, basename='statistics')



urlpatterns = [
    path('', include(router.urls)),
    path('vnpay/', include('vnpay.api_urls')),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
