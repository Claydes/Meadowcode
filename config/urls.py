from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.views import ProblemDetailPageView, ProblemListPageView


urlpatterns = [
    path("", ProblemListPageView.as_view(), name="frontend-problem-list"),
    path(
        "problems/<slug:slug>/",
        ProblemDetailPageView.as_view(),
        name="frontend-problem-detail",
    ),
    path("admin/", admin.site.urls),
    path("api/health/", include("apps.core.urls")),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/problems/", include("apps.problems.urls")),
    path("api/submissions/", include("apps.submissions.urls")),
    path("api/contests/", include("apps.contests.urls")),
    path("api/discussions/", include("apps.discussions.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
