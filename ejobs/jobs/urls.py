from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'jobs', views.JobViewSet, basename='job')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'apply', views.JobApplicationViewSet, basename='apply')
router.register(r'technology', views.TechnologyViewSet, basename='technology')
router.register(r'save_job', views.SaveJobViewSet, basename='save_job')



urlpatterns = [
    path('', include(router.urls)),
]
