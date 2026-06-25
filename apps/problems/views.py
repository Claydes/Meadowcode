from django.db.models import BooleanField, Exists, OuterRef, Value
from rest_framework import viewsets

from apps.core.permissions import IsAdminOrReadOnly

from .models import Problem, Tag, UserProblemProgress
from .serializers import ProblemSerializer, TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ("name", "slug")
    ordering_fields = ("name",)


class ProblemViewSet(viewsets.ModelViewSet):
    serializer_class = ProblemSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    filterset_fields = ("difficulty", "tags__slug", "is_published")
    search_fields = ("title", "statement")
    ordering_fields = ("created_at", "difficulty", "title")

    def get_queryset(self):
        queryset = (
            Problem.objects.select_related("author")
            .prefetch_related("tags", "test_cases")
            .all()
        )

        if self.request.user.is_authenticated:
            solved_progress = UserProblemProgress.objects.filter(
                user=self.request.user,
                problem_id=OuterRef("pk"),
            )
            queryset = queryset.annotate(is_solved=Exists(solved_progress))
        else:
            queryset = queryset.annotate(
                is_solved=Value(False, output_field=BooleanField())
            )

        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_published=True)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
