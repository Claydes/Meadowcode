from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Problem, Tag, TestCase


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ("id", "input_data", "expected_output", "is_sample", "order")


class ProblemSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    is_solved = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        many=True,
        required=False,
        write_only=True,
    )
    samples = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = (
            "id",
            "is_solved",
            "author",
            "tags",
            "tag_ids",
            "samples",
            "title",
            "slug",
            "statement",
            "examples",
            "constraints",
            "function_name",
            "function_arguments",
            "starter_code",
            "difficulty",
            "time_limit_ms",
            "memory_limit_mb",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    @extend_schema_field(TestCaseSerializer(many=True))
    def get_samples(self, obj):
        sample_cases = obj.test_cases.filter(is_sample=True)
        return TestCaseSerializer(sample_cases, many=True).data

    @extend_schema_field(serializers.BooleanField)
    def get_is_solved(self, obj) -> bool:
        return bool(getattr(obj, "is_solved", False))
