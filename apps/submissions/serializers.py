from rest_framework import serializers

from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "user",
            "problem",
            "problem_title",
            "language",
            "code",
            "status",
            "verdict_message",
            "runtime_ms",
            "memory_kb",
            "created_at",
            "judged_at",
        )
        read_only_fields = (
            "id",
            "user",
            "problem_title",
            "status",
            "verdict_message",
            "runtime_ms",
            "memory_kb",
            "created_at",
            "judged_at",
        )
