from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = []

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
