from django.db.models import Q
from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Job, User, Employer, Seeker, SaveJob, JobApplication, UserRole, CVStatus, Technology
from .serializer import JobSerializer, UserSerializer, EmployerSerializer, SeekerSerializer, SaveJobSerializer, \
    JobApplicationSerializer, JobApplicationCreateSerializer, FilterCVJobApplicationSerializer, TechnologySerializer


class IsEmployer(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập và có vai trò là employer
        return request.user.is_authenticated and request.user.role == UserRole.EMPLOYER


class IsSeeker(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra người dùng đã đăng nhập và có vai trò là seeker
        return request.user.is_authenticated and request.user.role == UserRole.JOB_SEEKER


class TechnologyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Technology.objects.all()
    serializer_class = TechnologySerializer


class UserViewSet(viewsets.GenericViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['retrieve', 'current_user', 'employer_detail', 'retrieve']:
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

    @action(detail=False, methods=['patch'], url_path='update_employer')
    def update_employer(self, request):
        user = request.user

        employer = Employer.objects.get(user=user)
        serializer = EmployerSerializer(employer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['patch'], url_path='update_seeker')
    def update_seeker(self, request):
        user = request.user
        # Lấy thông tin của người tìm việc liên kết với người dùng hiện tại
        seeker = Seeker.objects.get(user=user)
        serializer = SeekerSerializer(seeker, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            technology = request.data.get(Technology, [])
            if technology:
                seeker.technologies.set(technology)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


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

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        # Lấy các tham số tìm kiếm từ truy vấn
        technologies = request.query_params.getlist('technologies', [])
        salary = request.query_params.get('salary', None)
        location = request.query_params.get('location', None)
        experience = request.query_params.get('experience', None)

        # Tạo một đối tượng Q để xây dựng các điều kiện tìm kiếm
        query = Q(is_active=True)

        if technologies:
            # Tìm công việc với công nghệ phù hợp
            query &= Q(technologies__id__in=technologies)
        if salary:
            # Tìm công việc với mức lương
            query &= Q(salary__icontains=salary)
        if location:
            # Tìm công việc ở địa điểm cụ thể
            query &= Q(location__icontains=location)
        if experience:
            # Tìm công việc yêu cầu kinh nghiệm cụ thể
            query &= Q(experience__icontains=experience)

        # Áp dụng các điều kiện tìm kiếm cho queryset
        jobs = Job.objects.filter(query).distinct()
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)


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


class SaveJobViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        queryset = SaveJob.objects.filter(seeker=user)
        serializer = SaveJobSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        job_id = request.data.get('job_id')
        if not job_id:
            return Response({"detail": "Job ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        job = Job.objects.get(id=job_id)

        # Check if the job is already in the list
        if SaveJob.objects.filter(seeker=user, job=job).exists():
            return Response({"detail": "Job is already in the list"}, status=status.HTTP_400_BAD_REQUEST)

        save_job = SaveJob(seeker=user, job=job)
        save_job.save()

        serializer = SaveJobSerializer(save_job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        user = request.user
        try:
            save_job = SaveJob.objects.get(seeker=user, job_id=pk)
            save_job.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SaveJob.DoesNotExist:
            return Response({"detail": "Job not found in the list"}, status=status.HTTP_404_NOT_FOUND)



