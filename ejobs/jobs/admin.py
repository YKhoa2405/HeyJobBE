from django.contrib import admin
from django import forms
from .models import Job, User, Applications, Seeker, Employer, SaveJob


admin.site.register(Seeker)
admin.site.register(User)
admin.site.register(Employer)
admin.site.register(SaveJob)
admin.site.register(Job)
admin.site.register(Applications)

