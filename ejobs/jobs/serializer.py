from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Job, Employer, User, Seeker, UserRole, SaveJob, JobApplication, Technology, CVStatus, Follow


class TechnologySerializer(ModelSerializer):
    class Meta:
        model = Technology
        fields = ['id', 'name']


class EmployerSerializer(ModelSerializer):
    job_count = serializers.SerializerMethodField()
    pending_cv_count = serializers.SerializerMethodField()
    accepted_cv_count = serializers.SerializerMethodField()
    class Meta:
        model = Employer
        fields = ['user', 'company_name', 'website', 'size', 'address', 'description', 'approval_status', 'job_count', 'pending_cv_count', 'accepted_cv_count']
    def get_job_count(self, obj):
        return Job.objects.count()  # Assuming the related name for Job model is 'jobs'

    def get_pending_cv_count(self, obj):
        return JobApplication.objects.filter(job__employer=obj.user, status=CVStatus.PENDING).count()

    def get_accepted_cv_count(self, obj):
        return JobApplication.objects.filter(job__employer=obj.user, status=CVStatus.OPEN).count()

class SeekerSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True)
    saved_count = serializers.SerializerMethodField()  # Thêm trường để đếm số lượng việc làm đã lưu
    apply_count = serializers.SerializerMethodField()  # Thêm trường để đếm số lượng việc làm đã lưu

    class Meta:
        model = Seeker
        fields = ['user', 'experience', 'location', 'technologies', 'saved_count', 'apply_count']

    def get_saved_count(self, obj):
        # Đếm số lượng việc làm đã lưu cho seeker hiện tại
        return SaveJob.objects.filter(seeker=obj.user).count()

    def get_apply_count(self, obj):
        # Đếm số lượng việc làm đã lưu cho seeker hiện tại
        return JobApplication.objects.filter(seeker=obj.user).count()


class UserSerializer(ModelSerializer):
    employer = EmployerSerializer(read_only=True)
    seeker = SeekerSerializer(read_only=True)
    role = serializers.ChoiceField(choices=[(role.value, role.name) for role in UserRole])
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "avatar", "role",  "employer", "seeker"]


    def create(self, validated_data):
        role_value = validated_data.pop('role')
        role = UserRole(role_value)  # Chuyển đổi giá trị chuỗi thành Enum
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.role = role
        user.save()

        if role == UserRole.EMPLOYER:
            Employer.objects.create(user=user)
        elif role == UserRole.JOB_SEEKER:
            Seeker.objects.create(user=user)
        return user


class JobCreateSerializer(serializers.ModelSerializer):
    # Chọn các công nghệ bằng cách sử dụng id
    technologies = serializers.PrimaryKeyRelatedField(
        queryset=Technology.objects.all(),
        many=True
    )
    class Meta:
        model = Job
        fields = ['title', 'description', 'requirements', 'location', 'salary', 'expiration_date', 'experience', 'technologies', 'is_active']

class JobSerializer(serializers.ModelSerializer):
    employer = UserSerializer(read_only=True)
    technologies = TechnologySerializer(many=True)
    is_saved = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ['id', 'employer', 'title', 'location', 'salary', 'experience', 'technologies', 'created_at', 'expiration_date', 'description', 'requirements', 'is_saved', 'is_applied']
        read_only_fields = ['created_at', 'id']

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return SaveJob.objects.filter(seeker=user, job=obj).exists()
        return False

    def get_is_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return JobApplication.objects.filter(seeker=user, job=obj).exists()
        return False


class SaveJobSerializer(ModelSerializer):
    job = JobSerializer()

    class Meta:
        model = SaveJob
        fields = ["job", "created_date"]


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['cover_letter', 'cv', "name", "phone", "email"]


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    seeker = UserSerializer(read_only=True)
    cv = serializers.FileField(read_only=True)

    class Meta:
        model = JobApplication
        fields = ['seeker', 'cv']

class JobApplicationSerializer(ModelSerializer):
    job = JobSerializer()
    seeker = UserSerializer()

    class Meta:
        model = JobApplication
        fields = ["job", "seeker", "cover_letter", "status", "created_at", "cv", "name", "phone", "email"]


class FilterCVJobApplicationSerializer(serializers.ModelSerializer):
    job = serializers.SerializerMethodField()
    seeker_info = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'seeker_info', 'status', 'created_at', "cover_letter", "cv", "status", "name", "phone", "email"]

    def get_job(self, obj):
        job = obj.job
        return {
            'id': job.id,
            'title': job.title,
        }

    def get_seeker_info(self, obj):
        seeker = obj.seeker
        return {
            'id': seeker.id,
            'email': seeker.email,  # Hoặc bất kỳ thông tin nào bạn muốn hiển thị
            'username': seeker.username
        }


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['follower', 'following']



