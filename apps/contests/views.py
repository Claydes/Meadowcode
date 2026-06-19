from django.db import IntegrityError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly

from .models import Contest, ContestRegistration
from .serializers import ContestRegistrationSerializer, ContestSerializer


class ContestViewSet(viewsets.ModelViewSet):
    serializer_class = ContestSerializer
    lookup_field = "slug"
    filterset_fields = ("is_public",)
    search_fields = ("title", "description")
    ordering_fields = ("starts_at", "ends_at", "title")

    def get_queryset(self):
        queryset = Contest.objects.select_related("created_by").prefetch_related(
            "participants",
            "problems",
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_public=True)

    def get_permissions(self):
        if self.action == "join":
            return [permissions.IsAuthenticated()]
        return [IsAdminOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def join(self, request, slug=None):
        contest = self.get_object()
        try:
            registration = ContestRegistration.objects.create(
                contest=contest,
                user=request.user,
            )
        except IntegrityError:
            registration = ContestRegistration.objects.get(
                contest=contest,
                user=request.user,
            )
            response_status = status.HTTP_200_OK
        else:
            response_status = status.HTTP_201_CREATED

        serializer = ContestRegistrationSerializer(registration)
        return Response(serializer.data, status=response_status)
