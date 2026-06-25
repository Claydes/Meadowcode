from django.contrib import admin

from .models import Problem, Tag, TestCase, UserProblemProgress


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    inlines = [TestCaseInline]
    list_display = (
        "title",
        "function_name",
        "difficulty",
        "is_published",
        "created_at",
    )
    list_filter = ("difficulty", "is_published", "tags")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "statement")


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("problem", "is_sample", "order")
    list_filter = ("is_sample",)


@admin.register(UserProblemProgress)
class UserProblemProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "solved_at", "first_accepted_submission")
    list_filter = ("solved_at",)
    search_fields = ("user__username", "problem__title")
    readonly_fields = ("solved_at",)
