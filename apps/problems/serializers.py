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
            "author",
            "tags",
            "tag_ids",
            "samples",
            "title",
            "slug",
            "statement",
            "examples",
            "constraints",
            "difficulty",
            "time_limit_ms",
            "memory_limit_mb",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def get_samples(self, obj):
        sample_cases = obj.test_cases.filter(is_sample=True)
        return TestCaseSerializer(sample_cases, many=True).data
