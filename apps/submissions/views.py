from django.db import transaction
from rest_framework import permissions, viewsets

from apps.judge.tasks import run_submission

from .models import Submission
from .serializers import SubmissionSerializer


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("problem", "language", "status")
    ordering_fields = ("created_at", "runtime_ms", "memory_kb")

    def get_queryset(self):
        queryset = Submission.objects.select_related("user", "problem")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        submission = serializer.save(user=self.request.user)
        transaction.on_commit(lambda: run_submission.delay(submission.id))
