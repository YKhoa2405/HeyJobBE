from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job, User, Employer, Seeker, SaveJob, JobApplication, UserRole, CVStatus
from .serializer import JobSerializer, UserSerializer, EmployerSerializer, SeekerSerializer, SaveJobSerializer, \
    JobApplicationSerializer, JobApplicationCreateSerializer, FilterCVJobApplicationSerializer


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
    queryset = Job.objects.filter(is_active=True)
    serializer_class = JobSerializer

    def perform_create(self, serializer):  # khi gọi api create sẽ lấy user đang đăng nhập gán vào
        serializer.save(employer=self.request.user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Chỉ employer mới có thể tạo, cập nhật, hoặc xóa công việc
            return [permissions.IsAuthenticated(), IsEmployer()]
        # Cả employer và seeker đều có thể xem danh sách công việc
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='employer_jobs')
    def list_employer_jobs(self, request):
        # Hiển thị danh sách công việc của nhà tuyển dụng hiện tại
        jobs = Job.objects.filter(employer=request.user)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='employer_job_seeker')
    def get_employer_jobs(self, request, pk=None):
        # Lấy các công việc mà employer đã đăng
        jobs = Job.objects.filter(employer_id=pk, is_active=True)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='apply', permission_classes=[IsSeeker])
    def apply(self, request, pk=None):
        job = self.get_object()

        # Tạo một JobApplication mới
        data = {
            'job': job,
            'seeker': request.user,
            'cover_letter': request.data.get('cover_letter')
        }
        serializer = JobApplicationSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationViewSet(viewsets.GenericViewSet, generics.UpdateAPIView, generics.RetrieveAPIView):
    queryset = JobApplication.objects.all()

    def get_serializer_class(self):
        if self.action == ['apply_job']:
            return JobApplicationCreateSerializer
        # if self.action == ['seeker_job']:
        #     return FilterJobApplicationSerializer
        if self.action == ['employer_apply']:
            return FilterCVJobApplicationSerializer
        return JobApplicationSerializer

    def perform_create(self, serializer):
        # Tự động gán seeker là người dùng hiện tại
        serializer.save(seeker=self.request.user)

    def get_permissions(self):
        if self.action == ['apply_job', 'seeker_apply']:
            return [permissions.IsAuthenticated(), IsSeeker()]
        if self.action in ['employer_apply']:
            return [permissions.IsAuthenticated(), IsEmployer()]  # Hoặc quyền phù hợp cho nhà tuyển dụng
        return [permissions.AllowAny()]

    @action(methods=['post'], url_path='apply_job', detail=True)
    def apply_job(self, request, pk=None):
        job = get_object_or_404(Job, id=pk)

        if JobApplication.objects.filter(job=job, seeker=request.user).exists():
            return Response({'detail': 'You have already applied for this job.'}, status=status.HTTP_400_BAD_REQUEST)

        # Tạo dữ liệu để nộp đơn
        data = {
            'cover_letter': request.data.get('cover_letter'),
            'job': job.id,
            'seeker': request.user.id
        }

        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='seeker_apply') #Danh sách công việc đã ứng tuyển / Seeker
    def seeker_apply(self, request):
        seeker = request.user
        applications = JobApplication.objects.filter(seeker=seeker)
        serializer = JobApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='employer_apply') #Danh sách cv đã ứng tuyển / Employer
    def employer_apply(self, request):

        employer = request.user.id

        # Lấy các công việc của nhà tuyển dụng
        jobs = Job.objects.filter(employer=employer)

        # Lấy các đơn ứng tuyển cho các công việc này
        applications = JobApplication.objects.filter(job__in=jobs)
        serializer = FilterCVJobApplicationSerializer(applications, many=True)
        return Response(serializer.data)








