from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Job, Employer, User, Seeker, UserRole, SaveJob, JobApplication


class EmployerSerializer(ModelSerializer):
    class Meta:
        model = Employer
        fields = ['user', 'company_name', 'website', 'size', 'address', 'description']


class SeekerSerializer(ModelSerializer):
    class Meta:
        model = Seeker
        fields = ['user', 'experience', 'location', 'technology']

class UserSerializer(ModelSerializer):
    employer = EmployerSerializer(read_only=True)
    seeker = SeekerSerializer(read_only=True)
    role = serializers.ChoiceField(choices=[(role.value, role.name) for role in UserRole])
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "avatar", "role", "employer", "seeker"]

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


class JobSerializer(ModelSerializer):
    employer = UserSerializer(read_only=True)

    class Meta:
        model = Job
        fields = ['id', 'employer', 'title', 'location', 'salary', 'experience', 'technology', 'created_at', 'expiration_date']

        read_only_fields = ['created_at', 'id']


class SaveJobSerializer(ModelSerializer):
    job = JobSerializer()
    seeker = UserSerializer()

    class Meta:
        model = SaveJob
        fields = ["seeker", "job", "created_date"]


class JobApplicationSerializer(ModelSerializer):
    job = JobSerializer()
    seeker = UserSerializer()

    class Meta:
        model = JobApplication
        fields = ["job", "seeker", "cover_letter", "status", "created_at"]

        read_only_fields = ['created_at', 'status']
