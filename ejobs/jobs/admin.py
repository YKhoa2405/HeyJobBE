from django.contrib import admin

from .models import Job, User, JobApplication, Employer, Technology, Service


class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'role', 'is_active']
    search_fields = ['username', 'email']
    list_filter = ['role', 'is_active']
    ordering = ['-id']  # Sắp xếp theo id giảm dần


class EmployerAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'user']
    search_fields = ['company_name']
    ordering = ['company_name']  # Sắp xếp theo tên công ty


class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'employer']
    search_fields = ['title']
    list_filter = ['employer']


class ApplyJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'seeker', 'job', 'status']


class TechnologyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']



admin.site.register(User, UserAdmin)
admin.site.register(Employer, EmployerAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(JobApplication, ApplyJobAdmin)
admin.site.register(Technology)
admin.site.register(Service)


