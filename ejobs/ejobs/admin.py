from datetime import datetime

from django.contrib import admin
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from vnpay.models import Billing

from jobs.utils import get_statistics_user, get_statistics_job
from jobs.models import Job, Employer, Seeker, User, Service, Technology, EmployerService

class CustomAdminSite(admin.AdminSite):
    site_header = 'Quản trị hệ thống tìm kiếm việc làm'
    index_title = 'Chào mừng đến với trang quản trị'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats_user/', self.admin_view(self.stats_user_view), name='stats_user'),
            path('stats_job/', self.admin_view(self.stats_job_view), name='stats_job'),

        ]
        return custom_urls + urls

    def stats_user_view(self, request):
        statistics = get_statistics_user()

        # Trả về mẫu với dữ liệu thống kê
        context = {
            'statistics': statistics,
            'title': 'Thống kê người dùng',
        }
        return TemplateResponse(request, 'admin/stats_user.html', context)

    def stats_job_view(self, request):
        # Lấy tháng và năm từ GET request
        selected_month = request.GET.get('month', None)
        selected_year = request.GET.get('year', None)

        current_year = datetime.now().year  # Lấy năm hiện tại

        # Nếu tháng và năm không được chọn, mặc định là tháng hiện tại và năm hiện tại
        if not selected_month or not selected_year:
            selected_month = datetime.now().month
            selected_year = current_year

        job_statistics = get_statistics_job(selected_month, selected_year)  # Cập nhật hàm để nhận tháng và năm

        # Tạo danh sách các tháng và năm để hiển thị trong template
        months = list(range(1, 13))  # Tạo danh sách tháng từ 1 đến 12
        years = list(
            range(current_year - 5, current_year + 1))  # Tạo danh sách năm từ năm hiện tại - 5 đến năm hiện tại

        context = {
            'total_jobs': job_statistics['total_jobs'],
            'current_year': current_year,
            'selected_month': int(selected_month),
            'selected_year': int(selected_year),
            'months': months,
            'years': years,
            'active_jobs': job_statistics['active_jobs'],
            'expired_jobs': job_statistics['expired_jobs'],
        }
        return TemplateResponse(request, 'admin/stats_job.html', context)

class EmployerAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'user', 'approval_status']
    search_fields = ['company_name']
    ordering = ['company_name']  # Sắp xếp theo tên công ty

class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'employer']
    search_fields = ['title']
    list_filter = ['employer']

class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'role', 'is_active']
    search_fields = ['username', 'email']
    list_filter = ['role', 'is_active']
    ordering = ['-id']  # Sắp xếp theo id giảm dần


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


admin_site = CustomAdminSite(name='custom_admin')
admin_site.register(Billing)
admin_site.register(Job, JobAdmin)
admin_site.register(Employer, EmployerAdmin)
admin_site.register(User, UserAdmin)
admin_site.register(Technology)
admin_site.register(Service, ServiceAdmin)
admin_site.register(EmployerService)
