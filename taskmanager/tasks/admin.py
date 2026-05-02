from django.contrib import admin
from .models import Task

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'is_completed', 'created_at')

admin.site.register(Task, TaskAdmin)
