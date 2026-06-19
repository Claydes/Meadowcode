from rest_framework import serializers

from .models import DiscussionComment, DiscussionThread


class DiscussionCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DiscussionComment
        fields = ("id", "thread", "user", "body", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


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
