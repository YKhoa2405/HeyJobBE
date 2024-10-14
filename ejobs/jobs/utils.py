from datetime import datetime

from .models import User, Employer, Seeker, Job

from django.utils import timezone
def get_statistics_user():
    # Tổng số người dùng
    total_users = User.objects.count()

    # Tổng số nhà tuyển dụng
    total_employers = Employer.objects.count()

    # Số nhà tuyển dụng đã xác minh
    verified_employers = Employer.objects.filter(approval_status=True).count()

    # Tổng số ứng viên
    total_seekers = Seeker.objects.count()

    # Trả về kết quả dưới dạng dictionary
    return {
        'total_users': total_users-1,
        'total_employers': total_employers,
        'verified_employers': verified_employers,
        'total_seekers': total_seekers
    }


def get_statistics_job(month=None, year=None):
    # Truy vấn tổng số bài đăng
    if month and year:
        total_jobs = Job.objects.filter(
            created_date__month=month,
            created_date__year=year
        ).count()
    else:
        total_jobs = Job.objects.count()  # Đếm tổng số bài đăng tuyển dụng

    # Truy vấn số bài đăng còn hoạt động (active)
    active_jobs = Job.objects.filter(is_active=True).count()

    # Truy vấn số bài đăng đã hết hạn
    expired_jobs = Job.objects.filter(is_active=False).count()


    return {
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'expired_jobs': expired_jobs
    }
