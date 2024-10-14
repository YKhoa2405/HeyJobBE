from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Job, Employer, User, Seeker, UserRole, SaveJob, JobApplication, Technology, CVStatus, Follow, \
    Service, EmployerService


class TechnologySerializer(ModelSerializer):
    class Meta:
        model = Technology
        fields = ['id', 'name']


class EmployerSerializer(ModelSerializer):
    pending_cv_count = serializers.SerializerMethodField()
    accepted_cv_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()

    class Meta:
        model = Employer
        fields = ['user', 'company_name', 'website', 'size', 'address', 'description', 'approval_status', 'pending_cv_count', 'accepted_cv_count', 'followers_count', 'business_document']

    def get_pending_cv_count(self, obj):
        return JobApplication.objects.filter(job__employer=obj.user, status=CVStatus.PENDING).count()

    def get_accepted_cv_count(self, obj):
        return JobApplication.objects.filter(job__employer=obj.user, status=CVStatus.OPEN).count()

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj.user).count()


class SeekerSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True, read_only=True)
    class Meta:
        model = Seeker
        fields = ['user', 'experience', 'location', 'technologies']



class UserSerializer(ModelSerializer):
    employer = EmployerSerializer(read_only=True)
    seeker = SeekerSerializer(read_only=True)
    role = serializers.ChoiceField(choices=[(role.value, role.name) for role in UserRole])
    followed = serializers.SerializerMethodField()
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['avatar'] = instance.avatar.url
        return rep

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "avatar", "role",  "employer", "seeker", "followed"]

    def get_followed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False

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
    # technologies = TechnologySerializer(many=True)

    class Meta:
        model = Job
        fields = ['title', 'description', 'requirements', 'location', 'location_detail', 'salary', 'expiration_date', 'experience', 'technologies', 'is_active', 'quantity', 'latitude', 'longitude']


class JobSerializer(serializers.ModelSerializer):
    employer = UserSerializer(read_only=True)
    technologies = TechnologySerializer(many=True)
    is_saved = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ['id', 'employer', 'title', 'location', 'location_detail', 'salary', 'experience', 'technologies', 'expiration_date', 'description', 'requirements', 'is_saved', 'is_applied', 'quantity', 'is_active', 'latitude', 'longitude']
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
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['cv'] = instance.cv.url
        return rep
    class Meta:
        model = JobApplication
        fields = ['cover_letter', 'cv', "name", "phone", "email"]


class JobApplicationSerializer(ModelSerializer):
    job = JobSerializer()
    seeker = UserSerializer()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['cv'] = instance.cv.url
        return rep

    class Meta:
        model = JobApplication
        fields = ["job", "seeker", "cover_letter", "status", "created_at", "cv", "name", "phone", "email"]


class FilterCVJobApplicationSerializer(serializers.ModelSerializer):
    job = serializers.SerializerMethodField()
    seeker_info = serializers.SerializerMethodField()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['cv'] = instance.cv.url
        return rep
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
            'username': seeker.username,
        }


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['follower', 'following']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class PurchaseServiceSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), source='service')

    class Meta:
        model = EmployerService
        fields = ['service_id']

class EmployerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerService
        fields = '__all__'

