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
    avatar = CloudinaryField('avatar', blank=True)
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
    approval_status = models.BooleanField(default=False)

    def __str__(self):
        return f"Employer: {self.user.email}"


class Seeker(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    experience = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    technologies = models.ManyToManyField(Technology, null=True, blank=True)

    def __str__(self):
        return f"Seeker: {self.user.email}"


class EmployerImage(BaseModel):
    url = CloudinaryField(null=True, blank=True)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)


class EmployerDocument(BaseModel):
    employer = models.OneToOneField(Employer, on_delete=models.CASCADE)
    business_document = CloudinaryField(null=True, blank=True)
    tax_document = CloudinaryField(null=True, blank=True)

    def __str__(self):
        return f"Documents: {self.employer}"


class SeekerCompanyFollow(models.Model):
    seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('seeker', 'employer')  # Ensure a user can only follow a company once


class Job(BaseModel):
    employer = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=255)
    salary = models.CharField(max_length=255)
    expiration_date = models.DateTimeField()
    experience = models.CharField(max_length=20)
    technologies = models.ManyToManyField(Technology)
    created_at = BaseModel.created_date
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
    cv = CloudinaryField('cv')


class SaveJob(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_date']


