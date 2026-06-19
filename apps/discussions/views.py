from rest_framework import permissions, viewsets

from apps.core.permissions import IsOwnerOrAdminOrReadOnly

from .models import DiscussionComment, DiscussionThread
from .serializers import DiscussionCommentSerializer, DiscussionThreadSerializer


class DiscussionThreadViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionThreadSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdminOrReadOnly]
    filterset_fields = ("problem",)
    search_fields = ("title", "body")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        return DiscussionThread.objects.select_related("user", "problem").prefetch_related(
            "comments"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DiscussionCommentViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdminOrReadOnly]
    filterset_fields = ("thread",)
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        return DiscussionComment.objects.select_related("user", "thread")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
