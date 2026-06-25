from rest_framework import serializers

from .models import DiscussionComment, DiscussionThread


class DiscussionCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DiscussionComment
        fields = ("id", "thread", "user", "body", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate_thread(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        can_use_thread = (
            value.problem_id is None
            or value.problem.is_published
            or (user and user.is_staff)
        )
        if can_use_thread:
            return value
        raise serializers.ValidationError(
            "Cannot comment on a discussion for an unpublished problem."
        )


class DiscussionThreadSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = DiscussionThread
        fields = (
            "id",
            "user",
            "problem",
            "title",
            "body",
            "comments_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate_problem(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if value is None or value.is_published or (user and user.is_staff):
            return value
        raise serializers.ValidationError(
            "Cannot create a discussion for an unpublished problem."
        )
