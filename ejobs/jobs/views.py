from django.http import HttpResponse
from django.views import View
from django.shortcuts import render
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job, User, Employer, Seeker, SaveJob, JobApplication, UserRole
from .serializer import JobSerializer, UserSerializer, EmployerSerializer, SeekerSerializer, SaveJobSerializer, JobApplicationSerializer


class IsEmployer(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập và có vai trò là employer
        return request.user.is_authenticated and request.user.role == UserRole.EMPLOYER


class IsSeeker(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra người dùng đã đăng nhập và có vai trò là seeker
        return request.user.is_authenticated and request.user.role == UserRole.JOB_SEEKER


class UserViewSet(viewsets.GenericViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['retrieve', 'current_user', 'employer_detail']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(detail=False, methods=['get'], url_path='current_user')
    def current_user(self, request):
        user = request.user
        user_data = UserSerializer(user).data

        if user.role == UserRole.EMPLOYER.value:
            try:
                employer = Employer.objects.get(user=user)
                employer_data = EmployerSerializer(employer).data
                user_data['user_role_data'] = employer_data
            except Employer.DoesNotExist:
                user_data['user_role_data'] = None

        elif user.role == UserRole.JOB_SEEKER.value:
            try:
                seeker = Seeker.objects.get(user=user)
                seeker_data = SeekerSerializer(seeker).data
                user_data['user_role_data'] = seeker_data
            except Seeker.DoesNotExist:
                user_data['user_role_data'] = None

        return Response(user_data)

    @action(detail=True, methods=['get'], url_path='employer_detail')
    def employer_detail(self, request, pk=None):
        try:
            user = self.get_object()  # Lấy User theo pk
            user_data = UserSerializer(user).data
            employer = Employer.objects.get(user=user)
            employer_data = EmployerSerializer(employer).data
            user_data['employer'] = employer_data
            return Response(user_data)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)
        except Employer.DoesNotExist:
            return Response({"detail": "Employer data not found."}, status=404)


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all(is_active=True)
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def perform_create(self, serializer):  # khi gọi api create sẽ lấy user đang đăng nhập gán vào
        serializer.save(employer=self.request.user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsEmployer()]
        return [permissions.IsAuthenticated()]


class JobApplicationViewSet(viewsets.GenericViewSet):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer

    def get_permissions(self):
        if self.action in ['apply']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['post'], url_path='apply_job')
    def apply_for_job(self, request, pk=None):
        try:
            user = request.user

            # Kiểm tra xem người dùng có phải là Seeker không
            if not hasattr(user, 'seeker'):
                return Response({"detail": "Only job seekers can apply for jobs."}, status=status.HTTP_403_FORBIDDEN)

            job = self.get_object()  # Lấy đối tượng Job từ pk
            seeker = user.seeker  # Lấy đối tượng Seeker từ người dùng hiện tại
            data = request.data
            data['job'] = job.id
            data['seeker'] = seeker.id

            # Kiểm tra xem ứng viên đã ứng tuyển vào công việc này chưa
            if JobApplication.objects.filter(job=job, seeker=seeker).exists():
                return Response({"detail": "You have already applied for this job."},
                                status=status.HTTP_400_BAD_REQUEST)

            serializer = JobApplicationSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)







