import hashlib

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
import random
from datetime import timezone, timedelta, datetime

from django.core.mail import send_mail
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from vnpay.models import Billing
from django.utils.timezone import now
from django.utils import timezone
from geopy.distance import geodesic
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Job, User, Employer, Seeker, SaveJob, JobApplication, UserRole, CVStatus, Technology, Follow, \
    Service, EmployerService
from .pagination import JobPaginator
from .serializer import JobSerializer, UserSerializer, EmployerSerializer, SeekerSerializer, SaveJobSerializer, \
    JobApplicationSerializer, JobApplicationCreateSerializer, FilterCVJobApplicationSerializer, TechnologySerializer, \
    JobCreateSerializer, FollowSerializer, ServiceSerializer, PurchaseServiceSerializer, EmployerServiceSerializer
from django.conf import settings



class IsEmployer(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra xem người dùng đã đăng nhập và có vai trò là employer
        return request.user.is_authenticated and request.user.role == UserRole.EMPLOYER


class IsSeeker(permissions.BasePermission):
    def has_permission(self, request, view):
        # Kiểm tra người dùng đã đăng nhập và có vai trò là seeker
        return request.user.is_authenticated and request.user.role == UserRole.JOB_SEEKER


class TechnologyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Technology.objects.all().order_by('id')  # Sort by id
    serializer_class = TechnologySerializer

otp_storage = {}
class UserViewSet(viewsets.GenericViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['retrieve', 'current_user', 'employer_detail', 'retrieve', 'follow', 'following', 'unfollow', 'follower']:
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

    @action(detail=True, methods=['post'], url_path='follow')
    def follow(self, request, pk=None):
        follower = request.user

        # Kiểm tra nếu người dùng có vai trò là seeker
        if follower.role != UserRole.JOB_SEEKER:
            return Response({"detail": "Only job seekers can follow an employer."}, status=status.HTTP_403_FORBIDDEN)

        try:
            following_user = User.objects.get(pk=pk)

            # Kiểm tra xem người dùng đã theo dõi nhà tuyển dụng này chưa
            if Follow.objects.filter(follower=follower, following=following_user).exists():
                return Response({"detail": "You are already following this employer."}, status=status.HTTP_400_BAD_REQUEST)

            # Nếu chưa theo dõi, tạo mối quan hệ theo dõi mới
            Follow.objects.create(follower=follower, following=following_user)
            return Response({"detail": "You are now following this employer."}, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response({"detail": "Employer not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='unfollow')
    def unfollow(self, request, pk=None):
        user = request.user
        unfollow_user = User.objects.get(pk=pk)
        follow_relation = Follow.objects.filter(follower=user, following=unfollow_user).first()
        if follow_relation:
            follow_relation.delete()
            return Response({"detail": "You have unfollowed this employer."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "You were not following this employer."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='following')
    def following(self, request):
        user = request.user
        following_relations = Follow.objects.filter(follower=user)

        # Lấy danh sách các User mà user hiện tại đang theo dõi
        following_users = [relation.following for relation in following_relations]

        # Serialize dữ liệu của những người dùng đang theo dõi
        users_data = UserSerializer(following_users, many=True).data

        return Response(users_data)

    @action(detail=False, methods=['post'], url_path='send_otp')
    def send_otp(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email=email).first()

        if user:
            # Tạo mã OTP ngẫu nhiên
            otp = random.randint(1000, 9999)
            otp_storage[email] = (otp, timezone.now())  # Lưu OTP tạm thời

            # Không cần cache, chỉ gửi OTP cùng thời gian sống
            subject = "Mã OTP đặt lại mật khẩu"
            message = f"Mã OTP của bạn là: {otp}. Mã này sẽ hết hạn sau 120 giây."
            send_mail(subject, message, '2151050202khoa@ou.edu.vn', [email])

            return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        # Kiểm tra OTP
        if email in otp_storage:
            stored_otp, created_at = otp_storage[email]
            if stored_otp == int(otp) and (timezone.now() - created_at).seconds < 120:
                # Đổi mật khẩu
                user = User.objects.get(email=email)
                user.password = make_password(new_password)  # Mã hóa mật khẩu mới
                user.save()

                # Xóa OTP sau khi sử dụng
                del otp_storage[email]

                return Response(status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Email không tồn tại hoặc OTP không được gửi."}, status=status.HTTP_404_NOT_FOUND)



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
        jobs = Job.objects.filter(employer=request.user).order_by('-is_active')
        paginator = JobPaginator()
        page = paginator.paginate_queryset(jobs, request)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

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
        technologies = seeker.technologies.values_list('id', flat=True)

        query = Q(is_active=True, expiration_date__gte=current_time)

        if experience:
            query &= Q(experience__icontains=experience)
        if location:
            query &= Q(location__icontains=location)
        if technologies:  # Kiểm tra nếu seeker có công nghệ
            query &= Q(technologies__id__in=technologies)
        jobs = Job.objects.filter(query).distinct()

        paginator = JobPaginator()  # Tạo đối tượng phân trang
        page = paginator.paginate_queryset(jobs, request)  # Phân trang danh sách công việc

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)  # Trả về kết quả đã phân trang

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

        paginator = JobPaginator()  # Tạo một đối tượng phân trang
        page = paginator.paginate_queryset(jobs, request)  # Phân trang danh sách công việc

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby_jobs(self, request):
        # Lấy tọa độ và bán kính từ query parameters
        user_lat = request.query_params.get('latitude')
        user_lon = request.query_params.get('longitude')
        max_distance = request.query_params.get('distance', 5)

        # Kiểm tra xem tham số có hợp lệ không
        if not user_lat or not user_lon:
            return Response({"error": "Vui lòng cung cấp tọa độ latitude và longitude"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
            max_distance = float(max_distance)
        except ValueError:
            return Response({"error": "Tọa độ hoặc bán kính không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        jobs = Job.objects.filter(is_active=True)  # Lọc công việc đang hoạt động
        nearby_jobs = []

        for job in jobs:
            if job.latitude is not None and job.longitude is not None:
                job_location = (job.latitude, job.longitude)
                user_location = (user_lat, user_lon)
                distance = geodesic(user_location, job_location).kilometers

                if distance <= max_distance:
                    nearby_jobs.append(job)

        # Trả về danh sách công việc gần nhất
        serializer = self.get_serializer(nearby_jobs, many=True)
        return Response(serializer.data)


class JobApplicationViewSet(viewsets.GenericViewSet, generics.UpdateAPIView, generics.RetrieveAPIView,
                            generics.DestroyAPIView):
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
        cv = request.data.get('cv')
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')

        if not cover_letter or not cv:
            return Response({"detail": "Cover letter and CV are required."}, status=status.HTTP_400_BAD_REQUEST)

        print("CV:", cv)

        # Tạo đơn ứng tuyển mới
        job_application = JobApplication.objects.create(
            job=job,
            seeker=seeker,
            cover_letter=cover_letter,
            cv=cv,
            name=name,
            email=email,
            phone=phone
        )

        serializer = JobApplicationCreateSerializer(job_application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='seeker_apply')  # Danh sách công việc đã ứng tuyển / Seeker
    def seeker_apply(self, request):
        seeker = request.user
        applications = JobApplication.objects.filter(seeker=seeker)
        serializer = JobApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='employer_apply')  # Danh sách cv đã ứng tuyển / Employer
    def employer_apply(self, request):

        employer = request.user.id

        # Lấy các công việc của nhà tuyển dụng
        jobs = Job.objects.filter(employer=employer)

        # Lấy các đơn ứng tuyển cho các công việc này
        applications = JobApplication.objects.filter(job__in=jobs, status=CVStatus.OPEN)
        # Phân trang các đơn ứng tuyển
        paginator = JobPaginator()
        paginated_applications = paginator.paginate_queryset(applications, request)

        # Nếu có đơn ứng tuyển được phân trang
        if paginated_applications is not None:
            serializer = FilterCVJobApplicationSerializer(paginated_applications, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = FilterCVJobApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='employer_apply_new')  # Danh sách cv đã ứng tuyển / Employer
    def employer_apply_new(self, request):

        employer = request.user.id

        # Lấy các công việc của nhà tuyển dụng
        jobs = Job.objects.filter(employer=employer)

        # Lấy các đơn ứng tuyển cho các công việc này
        applications = JobApplication.objects.filter(job__in=jobs, status__in=[CVStatus.PENDING, CVStatus.CLOSED])

        paginator = JobPaginator()
        paginated_applications = paginator.paginate_queryset(applications, request)

        # Nếu có đơn ứng tuyển được phân trang
        if paginated_applications is not None:
            serializer = FilterCVJobApplicationSerializer(paginated_applications, many=True)
            return paginator.get_paginated_response(serializer.data)

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


class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

    def get_queryset(self):
        # Chỉ lấy các bản ghi Follow mà follower là người dùng hiện tại
        return Follow.objects.filter(follower=self.request.user)

    @action(detail=False, methods=['post'], url_path='follow')
    def follow_user(self, request):
        follower = request.user

        following_id = request.data.get('following_id')
        following = User.objects.get(id=following_id)

        if follower == following:
            return Response({'error': 'You cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = Follow.objects.get_or_create(follower=follower, following=following)
        if created:
            return Response({'status': 'followed'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'already followed'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='unfollow')
    def unfollow_user(self, request):
        follower = request.user
        following_id = request.data.get('following_id')
        following = User.objects.get(id=following_id)

        follow = Follow.objects.filter(follower=follower, following=following).first()
        if follow:
            follow.delete()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'not following'}, status=status.HTTP_400_BAD_REQUEST)


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    @action(detail=True, methods=['post'])
    def purchase(self, request, pk):
        service = Service.objects.get(pk=pk)
        user = request.user  # Người dùng đã xác thực

        # Kiểm tra thông tin hóa đơn
        transaction_no = request.data.get("vnp_TransactionNo")
        if not transaction_no:
            return Response({"message": "Mã giao dịch không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bill = Billing.objects.get(reference_number=transaction_no)
        except Billing.DoesNotExist:
            return Response({"message": "Hóa đơn không tồn tại"}, status=status.HTTP_400_BAD_REQUEST)

        # Cập nhật thông tin hóa đơn
        bill.result_payment = request.data.get("vnp_TransactionStatus")
        bill.is_paid = bill.result_payment == "00"  # Kiểm tra trạng thái thanh toán
        bill.transaction_id = transaction_no
        pay_at_str = request.data.get("vnp_PayDate")

        if pay_at_str:
            bill.pay_at = datetime.strptime(pay_at_str, '%Y%m%d%H%M%S')
        bill.save()

        # Kiểm tra dịch vụ đã tồn tại
        existing_service = EmployerService.objects.filter(user=user, service=service, is_active=True).first()

        if existing_service:
            # Cập nhật ngày kết thúc nếu dịch vụ đã hoạt động
            existing_service.end_date = timezone.now() + timedelta(
                days=30 * service.duration)  # Điều chỉnh thời gian nếu cần
            existing_service.save()
            return Response({'status': 'Dịch vụ đã được cập nhật'}, status=status.HTTP_200_OK)

        # Tạo bản ghi EmployerService mới
        end_date = timezone.now() + timedelta(days=30 * service.duration)  # Điều chỉnh thời gian nếu cần
        EmployerService.objects.create(
            user=user,
            service=service,
            end_date=end_date,
            amount=service.price,
        )

        return Response({'status': 'Dịch vụ đã được mua'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def purchased_services(self, request):
        user = request.user  # Lấy người dùng đã xác thực

        # Lấy danh sách dịch vụ đã mua của người dùng
        purchased_services = EmployerService.objects.filter(user=user).select_related('service')

        # Chuyển đổi danh sách dịch vụ thành serializer
        serializer = EmployerServiceSerializer(purchased_services, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class EmployerStatisticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # Chỉ cho phép người dùng đã xác thực

    def _has_active_service(self, employer_id):
        # Kiểm tra xem nhà tuyển dụng có dịch vụ với tên "Thống kê" và còn hoạt động không
        active_service = EmployerService.objects.filter(
            user_id=employer_id,
            service__id=2,
            is_active=True
        ).exists()
        return active_service
    def list(self, request):
        employer_id = request.user.id
        if not self._has_active_service(employer_id):
            return Response({'detail': 'Bạn chưa mua dịch vụ "Thống kê" hoặc dịch vụ đã hết hạn.'}, status=status.HTTP_403_FORBIDDEN)
        year = request.query_params.get('year')

        # Đếm số lượng công việc đang hoạt động (is_active = True)
        active_jobs_count = Job.objects.filter(employer_id=employer_id, is_active=True).count()

        # Đếm số lượng công việc đã hết hạn
        expired_jobs_count = Job.objects.filter(employer_id=employer_id, is_active=False).count()


        total_spent_on_services = Billing.objects.filter(pay_by=employer_id).aggregate(total=Sum('amount'))['total'] or 0

        # Tổng số đơn ứng tuyển theo tháng
        applications_per_month_query = JobApplication.objects.filter(job__employer_id=employer_id)
        if year:
            applications_per_month_query = applications_per_month_query.filter(created_date__year=year)

        applications_per_month = applications_per_month_query \
            .annotate(month=TruncMonth('created_date')) \
            .values('month') \
            .annotate(applications_count=Count('id')) \
            .order_by('month')
        # Tạo dictionary thống kê
        statistics = {      # Tổng số công việc đã đăng
            'active_jobs': active_jobs_count,             # Số công việc đang hoạt động
            'expired_jobs': expired_jobs_count,           # Số công việc đã hết hạn
            'total_spent_on_services': total_spent_on_services,
            'applications_per_month': list(applications_per_month)
        }

        return Response(statistics)

    @action(detail=False, methods=['get'])
    def applications_per_month(self, request):
        employer_id = request.user.id
        if not self._has_active_service(employer_id):
            return Response({'detail': 'Bạn chưa mua dịch vụ "Thống kê" hoặc dịch vụ đã hết hạn.'}, status=status.HTTP_403_FORBIDDEN)

        year = request.query_params.get('year')  # Lấy tham số năm từ request
        month = request.query_params.get('month')  # Lấy tham số tháng từ request

        # Lọc tất cả các job của employer hiện tại
        jobs_queryset = Job.objects.filter(employer_id=employer_id)

        # Lọc các Job theo thời gian tạo việc làm
        if year:
            jobs_queryset = jobs_queryset.filter(created_date__year=year)
        if month:
            jobs_queryset = jobs_queryset.filter(created_date__month=month)

        # Đếm số lượng đơn ứng tuyển theo từng công việc
        job_applications_counts = jobs_queryset.annotate(
            applications_count=Count(
                'jobapplication',
                filter=Q(jobapplication__created_date__year=year) & Q(jobapplication__created_date__month=month) if month else
                Q(jobapplication__created_date__year=year)
            )
        ).values('title', 'applications_count').order_by('title')

        return Response({
            'job_applications_counts': list(job_applications_counts)
        })



