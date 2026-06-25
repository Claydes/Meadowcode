from rest_framework import serializers

from .models import Language, Submission


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

    def validate_language(self, value):
        if value != Language.PYTHON:
            raise serializers.ValidationError(
                "Only Python submissions are supported right now."
            )
        return value

    def validate_problem(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if value.is_published or (user and user.is_staff):
            return value
        raise serializers.ValidationError("Cannot submit to an unpublished problem.")
