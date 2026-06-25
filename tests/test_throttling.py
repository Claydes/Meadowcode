from django.conf import settings

from apps.accounts.views import RegisterAPIView
from apps.discussions.views import DiscussionCommentViewSet, DiscussionThreadViewSet
from apps.submissions.views import SubmissionViewSet
from config.urls import ThrottledTokenObtainPairView, ThrottledTokenRefreshView


def test_api_throttling_is_configured_for_risky_endpoints():
    assert "rest_framework.throttling.AnonRateThrottle" in settings.REST_FRAMEWORK[
        "DEFAULT_THROTTLE_CLASSES"
    ]
    assert "rest_framework.throttling.UserRateThrottle" in settings.REST_FRAMEWORK[
        "DEFAULT_THROTTLE_CLASSES"
    ]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["submissions"]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["discussions"]

    assert ThrottledTokenObtainPairView.throttle_scope == "auth"
    assert ThrottledTokenRefreshView.throttle_scope == "auth"
    assert RegisterAPIView.throttle_scope == "auth"
    assert SubmissionViewSet.throttle_scope == "submissions"
    assert DiscussionThreadViewSet.throttle_scope == "discussions"
    assert DiscussionCommentViewSet.throttle_scope == "discussions"
