from django.db.models import Q
from django.http import HttpResponse
from django.utils.timezone import now
from django.views import View
from django.shortcuts import render, get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Job, User, Employer, Seeker, SaveJob, JobApplication, UserRole, CVStatus, Technology
from .serializer import JobSerializer, UserSerializer, EmployerSerializer, SeekerSerializer, SaveJobSerializer, \
    JobApplicationSerializer, JobApplicationCreateSerializer, FilterCVJobApplicationSerializer, TechnologySerializer, \
    JobApplicationDetailSerializer, JobCreateSerializer


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

    def get_serializer_class(self):
        if self.action == 'create':
            return JobCreateSerializer
        return JobSerializer

    def perform_create(self, serializer):
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

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        current_time = now()
        # Lấy các tham số tìm kiếm từ truy vấn
        technologies = request.query_params.getlist('technologies', [])
        salary = request.query_params.get('salary', None)
        location = request.query_params.get('location', None)
        experience = request.query_params.get('experience', None)
        title = request.query_params.get('title', None)

        # Tạo một đối tượng Q để xây dựng các điều kiện tìm kiếm
        query = Q(is_active=True, expiration_date__gte=current_time)

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
        if title:
            # Tìm công việc với tiêu đề cụ thể
            query &= Q(title__icontains=title)

        # Áp dụng các điều kiện tìm kiếm cho queryset
        jobs = Job.objects.filter(query).distinct()
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='jobs_by_employer')
    # Danh sách công việc của nhà tuyển dụng mà seeker có thể xem
    def jobs_by_employer(self, request, pk=None):
        current_time = now()

        jobs = Job.objects.filter(
            employer_id=pk,
            is_active=True,
            expiration_date__gte=current_time  # Lọc các công việc chưa hết hạn
        )
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='recommend')
    # Danh sách việc làm đề xuất cho ứng viên
    def recommend(self, request):
        current_time = now()
        seeker = request.user.seeker
        experience = seeker.experience
        location = seeker.location

        query = Q(is_active=True, expiration_date__gte=current_time)

        if experience:
            query &= Q(experience__icontains=experience)
        if location:
            query &= Q(location__icontains=location)

        jobs = Job.objects.filter(query).distinct()

        # Sử dụng serializer để trả về dữ liệu
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='high_salary')
    def high_salary_jobs(self, request):
        current_time = now()
        # Lọc các công việc có mức lương từ 20 triệu trở lên
        jobs = Job.objects.filter(
            is_active=True,
            expiration_date__gte=current_time,
            salary__in=['20 - 25 triệu', '25 - 30 triệu', '30 - 50 triệu', 'Trên 50 triệu']
        ).order_by('-salary')[:20]  # Lấy 20 công việc có mức lương cao nhất

        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

class JobApplicationViewSet(viewsets.GenericViewSet, generics.UpdateAPIView, generics.RetrieveAPIView, generics.DestroyAPIView):
    queryset = JobApplication.objects.all()

    def get_serializer_class(self):
        if self.action == ['apply_job']:
            return JobApplicationCreateSerializer
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

    @action(methods=['post'], url_path='apply_job', detail=True, permission_classes=[IsAuthenticated])
    def apply_job(self, request, pk=None):
        job = Job.objects.get(pk=pk)
        seeker = request.user  # Lấy đối tượng seeker từ người dùng hiện tại


        # Lấy dữ liệu từ yêu cầu
        cover_letter = request.data.get('cover_letter')
        cv = request.FILES.get('cv')

        if not cover_letter or not cv:
            return Response({"detail": "Cover letter and CV are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Tạo đơn ứng tuyển mới
        job_application = JobApplication.objects.create(
            job=job,
            seeker=seeker,
            cover_letter=cover_letter,
            cv=cv
        )

        serializer = JobApplicationCreateSerializer(job_application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        applications = JobApplication.objects.filter(job__in=jobs, status=CVStatus.OPEN)
        serializer = FilterCVJobApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='employer_apply_new') #Danh sách cv đã ứng tuyển / Employer
    def employer_apply_new(self, request):

        employer = request.user.id

        # Lấy các công việc của nhà tuyển dụng
        jobs = Job.objects.filter(employer=employer)

        # Lấy các đơn ứng tuyển cho các công việc này
        applications = JobApplication.objects.filter(job__in=jobs, status__in=[CVStatus.PENDING, CVStatus.CLOSED])
        serializer = FilterCVJobApplicationSerializer(applications, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=['get'], url_path='apply_detail')
    def apply_detail(self, request, pk=None):
        try:
            job_application = JobApplication.objects.get(pk=pk)
        except JobApplication.DoesNotExist:
            return Response({"detail": "Job application not found."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the data
        serializer = JobApplicationDetailSerializer(job_application)
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



