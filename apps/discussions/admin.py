from django.contrib import admin

from .models import DiscussionComment, DiscussionThread


class DiscussionCommentInline(admin.TabularInline):
    model = DiscussionComment
    extra = 0


@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    inlines = [DiscussionCommentInline]
    list_display = ("title", "user", "problem", "created_at")
    search_fields = ("title", "body", "user__username", "problem__title")


@admin.register(DiscussionComment)
class DiscussionCommentAdmin(admin.ModelAdmin):
    list_display = ("thread", "user", "created_at")
    search_fields = ("body", "user__username", "thread__title")
