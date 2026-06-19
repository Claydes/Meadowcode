from rest_framework import serializers

from apps.problems.serializers import ProblemSerializer

from .models import Contest, ContestProblem, ContestRegistration


class ContestProblemSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)

    class Meta:
        model = ContestProblem
        fields = ("id", "problem", "order", "points")


class ContestSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    contest_problems = serializers.SerializerMethodField()
    participants_count = serializers.IntegerField(
        source="participants.count",
        read_only=True,
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contest
        fields = (
            "id",
            "created_by",
            "contest_problems",
            "participants_count",
            "title",
            "slug",
            "description",
            "starts_at",
            "ends_at",
            "is_public",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_contest_problems(self, obj):
        queryset = ContestProblem.objects.select_related("problem").filter(contest=obj)
        return ContestProblemSerializer(queryset, many=True).data


class ContestRegistrationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    contest = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = ContestRegistration
        fields = ("id", "contest", "user", "joined_at")
