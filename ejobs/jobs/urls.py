from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'jobs', views.JobViewSet, basename='job')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'apply', views.JobApplicationViewSet, basename='apply')


urlpatterns = [
    path('', include(router.urls)),
]
