from datetime import timezone

from dateutil.relativedelta import relativedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from enum import Enum
from enumchoicefield import EnumChoiceField
from cloudinary.models import CloudinaryField


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Technology(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class UserRole(Enum):
    EMPLOYER = 'Nha tuyen dung'
    JOB_SEEKER = 'Ung vien'


class User(AbstractUser):
    avatar = CloudinaryField()
    email = models.EmailField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    role = EnumChoiceField(UserRole, default=None, null=True, blank=True)


class Employer(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(max_length=255, unique=True, null=True, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    business_document = CloudinaryField(null=True, blank=True)
    approval_status = models.BooleanField(default=False)

    def __str__(self):
        return f"Employer: {self.user.email}"


class Seeker(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    experience = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    technologies = models.ManyToManyField(Technology, blank=True)

    def __str__(self):
        return f"Seeker: {self.user.email}"


class EmployerImage(BaseModel):
    url = CloudinaryField()
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_user')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_following')

    class Meta:
        unique_together = ('follower', 'following')




class Job(BaseModel):
    employer = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=255)
    location_detail = models.CharField(max_length=255)
    salary = models.CharField(max_length=255)
    expiration_date = models.DateTimeField()
    experience = models.CharField(max_length=20)
    technologies = models.ManyToManyField(Technology)
    created_at = BaseModel.created_date
    quantity = models.IntegerField(null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.title


class CVStatus(Enum):
    OPEN = 'open' #Chấp nhận cv, chờ phỏng vấn
    CLOSED = 'closed'
    PENDING = 'pending'


#Đơn ứng tuyển
class JobApplication(BaseModel):
    created_at = BaseModel.created_date
    cover_letter = models.TextField()
    status = EnumChoiceField(CVStatus, default=CVStatus.PENDING)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(User, on_delete=models.CASCADE)
    cv = CloudinaryField()
    email = models.EmailField()
    phone = models.CharField(max_length=11)
    name = models.CharField(max_length=255)


class SaveJob(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_date']


class Service(models.Model):
    name = models.CharField(max_length=100)  # Tên dịch vụ
    description = models.TextField(null=True, blank=True)  # Mô tả dịch vụ
    description_detail = models.TextField(null=True, blank=True)  # Mô tả dịch vụ
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Giá của dịch vụ
    duration = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class EmployerService(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Tính toán ngày hết hạn dịch vụ dựa trên duration
        if not self.end_date:
            self.end_date = self.start_date + relativedelta(months=self.service.duration)
        super().save(*args, **kwargs)

    @property
    def is_service_active(self):
        # Kiểm tra xem dịch vụ còn hoạt động không
        return self.is_active and timezone.now() < self.end_date

