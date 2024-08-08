from django.db import models
from django.contrib.auth.models import AbstractUser
from enum import Enum
from enumchoicefield import EnumChoiceField


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class UserRole(Enum):
    EMPLOYER = 'Nha tuyen dung'
    JOB_SEEKER = 'Ung vien'


class User(AbstractUser):
    avatar = models.ImageField(upload_to='uploads/%Y/%m')
    email = models.EmailField(max_length=50, unique=True)

    def get_role(self):
        if hasattr(self, 'employer'):
            return UserRole.EMPLOYER.name
        elif hasattr(self, 'seeker'):
            return UserRole.JOB_SEEKER.name
        return None


class Employer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    website = models.URLField(max_length=255, unique=True)
    size = models.PositiveIntegerField()
    address = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=False)


class Seeker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    experience = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255)
    technology = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)


class Job(BaseModel):
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255)
    expiration_date = models.DateTimeField
    experience = models.CharField(max_length=20)
    technology = models.CharField(max_length=255)
    created_at = BaseModel.created_date
    is_active = BaseModel.is_active


    def __str__(self):
        return self.title


class CVStatus(Enum):
    OPEN = 'open' #Chấp nhận cv, chờ phỏng vấn
    CLOSED = 'closed'
    PENDING = 'pending'


#Đơn ứng tuyển
class Applications(BaseModel):
    created_at = BaseModel.created_date
    cover_letter = models.TextField()
    status = EnumChoiceField(CVStatus, default=CVStatus.PENDING)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE)


class SaveJob(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE)

