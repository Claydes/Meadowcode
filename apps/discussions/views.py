from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.throttling import ScopedRateThrottle

from apps.core.permissions import IsOwnerOrAdminOrReadOnly

from .models import DiscussionComment, DiscussionThread
from .serializers import DiscussionCommentSerializer, DiscussionThreadSerializer


class DiscussionThreadViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionThreadSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrAdminOrReadOnly,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "discussions"
    filterset_fields = ("problem",)
    search_fields = ("title", "body")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = (
            DiscussionThread.objects.select_related("user", "problem")
            .prefetch_related("comments")
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(
            Q(problem__isnull=True) | Q(problem__is_published=True)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DiscussionCommentViewSet(viewsets.ModelViewSet):
    serializer_class = DiscussionCommentSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrAdminOrReadOnly,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "discussions"
    filterset_fields = ("thread",)
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = DiscussionComment.objects.select_related(
            "user",
            "thread",
            "thread__problem",
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(
            Q(thread__problem__isnull=True) | Q(thread__problem__is_published=True)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
