from rest_framework.routers import DefaultRouter

from .views import DiscussionCommentViewSet, DiscussionThreadViewSet


router = DefaultRouter()
router.register("threads", DiscussionThreadViewSet, basename="discussion-thread")
router.register("comments", DiscussionCommentViewSet, basename="discussion-comment")

urlpatterns = router.urls
