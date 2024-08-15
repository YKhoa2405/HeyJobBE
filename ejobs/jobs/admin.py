from django.contrib import admin
from django import forms
from .models import Job, User, JobApplication, Seeker, Employer, SaveJob, SeekerCompanyFollow, Technology


class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'role', 'is_active']


class SeekerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user']


class EmployerAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'user']


class ApplyJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'seeker', 'job', 'status']


class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'employer']


class SaveJobAdmin(admin.ModelAdmin):
    list_display = ['seeker', 'job', 'created_date']


admin.site.register(Seeker, SeekerAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Employer, EmployerAdmin)
admin.site.register(SaveJob, SaveJobAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(JobApplication, ApplyJobAdmin)
admin.site.register(Technology)
