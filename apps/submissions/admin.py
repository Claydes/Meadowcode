from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "problem", "language", "status", "created_at")
    list_filter = ("language", "status", "created_at")
    search_fields = ("user__username", "problem__title", "code")
    readonly_fields = ("created_at", "judged_at")
