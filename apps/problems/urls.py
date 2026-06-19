from rest_framework.routers import DefaultRouter

from .views import ProblemViewSet, TagViewSet


router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("", ProblemViewSet, basename="problem")

urlpatterns = router.urls
