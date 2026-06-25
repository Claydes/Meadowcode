from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()


class HealthCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses=HealthCheckSerializer)
    def get(self, request):
        return Response({"status": "ok"})


class ProblemListPageView(TemplateView):
    template_name = "frontend/problem_list.html"


class ProblemDetailPageView(TemplateView):
    template_name = "frontend/problem_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["problem_slug"] = self.kwargs["slug"]
        return context
