from django.contrib import admin

from .models import Contest, ContestProblem, ContestRegistration


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    extra = 1


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    inlines = [ContestProblemInline]
    list_display = ("title", "starts_at", "ends_at", "is_public")
    list_filter = ("is_public", "starts_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "description")


@admin.register(ContestRegistration)
class ContestRegistrationAdmin(admin.ModelAdmin):
    list_display = ("contest", "user", "joined_at")
    search_fields = ("contest__title", "user__username")
