from django.contrib import admin

from .models import Problem, Tag, TestCase


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
    list_display = ("title", "difficulty", "is_published", "created_at")
    list_filter = ("difficulty", "is_published", "tags")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "statement")


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("problem", "is_sample", "order")
    list_filter = ("is_sample",)
